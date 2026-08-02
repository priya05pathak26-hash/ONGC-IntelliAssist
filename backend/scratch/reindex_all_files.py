import sys
import os
import shutil
from pathlib import Path
import json

sys.path.insert(0, os.getcwd())

from app.database import SessionLocal
from app.config import get_settings
from app.models import Document, DocumentChunk, User
from app.services.extractors import extract_text
from app.services.text_tools import chunk_text, embedding
from app.services.vector_db import rebuild_kb_index, rebuild_user_index

def main():
    settings = get_settings()
    db = SessionLocal()
    
    print("Deleting all existing document chunks from database...")
    db.query(DocumentChunk).delete()
    db.commit()
    print("Cleared existing chunks.")
    
    documents = db.query(Document).all()
    print(f"Re-chunking and re-embedding {len(documents)} documents...")
    
    for doc in documents:
        suffix = Path(doc.filename).suffix.lower()
        if doc.is_kb:
            stored_path = settings.knowledge_base_dir / f"{doc.content_hash}{suffix}"
        else:
            stored_path = settings.upload_dir / f"{doc.content_hash}{suffix}"
            
        if not stored_path.exists():
            print(f"Warning: File not found at {stored_path}, skipping.")
            continue
            
        print(f"Processing: {doc.filename} ({stored_path.name})...")
        try:
            all_pages = list(extract_text(stored_path))
            non_empty_pages = [(p, t) for (p, t) in all_pages if t and str(t).strip()]
            
            chunk_index = 0
            for page_number, text in non_empty_pages:
                # Uses the new optimized chunk_text with size=1500, overlap=350
                chunks = chunk_text(text)
                for chunk in chunks:
                    chunk_index += 1
                    db.add(
                        DocumentChunk(
                            document_id=doc.id,
                            page_number=page_number,
                            chunk_index=chunk_index,
                            text=chunk,
                            embedding=json.dumps(embedding(chunk)),
                        )
                    )
            db.commit()
            print(f"  Successfully indexed {chunk_index} chunks for {doc.filename}")
        except Exception as e:
            print(f"  Error processing {doc.filename}: {e}")
            db.rollback()
            
    print("\nDeleting old FAISS vectors on disk...")
    kb_path = settings.vector_db_dir / "knowledge_vectors"
    upload_path = settings.vector_db_dir / "upload_vectors"
    
    if kb_path.exists():
        shutil.rmtree(kb_path)
        print(f"Deleted: {kb_path}")
    if upload_path.exists():
        shutil.rmtree(upload_path)
        print(f"Deleted: {upload_path}")
        
    print("\nRebuilding Knowledge Base FAISS index (16384 dimensions)...")
    vs_kb = rebuild_kb_index(db)
    if vs_kb:
        print("Successfully rebuilt Knowledge Base FAISS index!")
    else:
        print("Knowledge Base is empty.")
        
    print("\nRebuilding User Uploads FAISS indexes...")
    users = db.query(User).all()
    for user in users:
        vs_user = rebuild_user_index(db, user.id)
        if vs_user:
            print(f"Successfully rebuilt FAISS index for user {user.email}!")
            
    db.close()
    print("\nAll documents re-indexed and FAISS indexes rebuilt successfully!")

if __name__ == "__main__":
    main()
