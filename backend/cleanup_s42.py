"""
Cleanup script to remove S-42_Manual.txt from database and vector indexes.
Run this once to purge the document from all storage.
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import Document, DocumentChunk
from sqlalchemy import func

settings = get_settings()

def remove_s42_manual():
    """Remove S-42_Manual.txt from database and rebuild affected indexes."""
    print("S-42_Manual.txt Cleanup Script")
    print("=" * 50)
    
    with SessionLocal() as db:
        # Find the document
        s42_doc = db.query(Document).filter(
            Document.filename.ilike("%S-42_Manual%")
        ).first()
        
        if not s42_doc:
            # Try broader search
            s42_doc = db.query(Document).filter(
                Document.filename.ilike("%S-42%")
            ).first()
        
        if not s42_doc:
            print("\n S-42_Manual.txt not found in database. Nothing to clean up.")
            return
        
        print(f"\n Found document:")
        print(f"  ID: {s42_doc.id}")
        print(f"  Filename: {s42_doc.filename}")
        print(f"  Is KB: {s42_doc.is_kb}")
        print(f"  Uploaded by: {s42_doc.uploaded_by_id}")
        
        # Count chunks
        chunk_count = db.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.document_id == s42_doc.id
        ).scalar() or 0
        
        print(f"  Chunks: {chunk_count}")
        
        # Delete chunks
        if chunk_count > 0:
            print(f"\n  Deleting {chunk_count} chunks...")
            db.query(DocumentChunk).filter(
                DocumentChunk.document_id == s42_doc.id
            ).delete(synchronize_session=False)
        
        # Delete document
        print(f"  Deleting document record...")
        db.delete(s42_doc)
        db.commit()
        
        print(f"\n [OK] Document and chunks removed from database")
        
        # Rebuild affected vector index
        user_id = s42_doc.uploaded_by_id
        is_kb = s42_doc.is_kb
        
        print(f"\n Rebuilding vector index...")
        
        if is_kb:
            from app.services.vector_db import rebuild_kb_index
            rebuild_kb_index(db)
            print(f"  [OK] KB vector index rebuilt")
        else:
            from app.services.vector_db import rebuild_user_index
            if user_id:
                rebuild_user_index(db, user_id)
                print(f"  [OK] User {user_id} vector index rebuilt")
        
        # Verify removal
        verify = db.query(Document).filter(
            Document.filename.ilike("%S-42%")
        ).first()
        
        if verify:
            print(f"\n [WARNING] Document still exists in database!")
        else:
            print(f"\n [OK] Verification: S-42_Manual.txt completely removed")
        
        print(f"\n{'=' * 50}")
        print(f"Cleanup complete!")
        print(f"{'=' * 50}")

if __name__ == "__main__":
    try:
        remove_s42_manual()
    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
