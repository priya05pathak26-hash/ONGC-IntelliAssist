import sys
import os
import shutil
from pathlib import Path

sys.path.insert(0, os.getcwd())

from app.database import SessionLocal
from app.config import get_settings
from app.services.vector_db import rebuild_kb_index, rebuild_user_index
from app.models import User

def main():
    settings = get_settings()
    db = SessionLocal()
    
    print("Deleting old FAISS vectors on disk...")
    kb_path = settings.vector_db_dir / "knowledge_vectors"
    upload_path = settings.vector_db_dir / "upload_vectors"
    
    if kb_path.exists():
        shutil.rmtree(kb_path)
        print(f"Deleted: {kb_path}")
    if upload_path.exists():
        shutil.rmtree(upload_path)
        print(f"Deleted: {upload_path}")
        
    print("\nRebuilding Knowledge Base FAISS index...")
    vs_kb = rebuild_kb_index(db)
    if vs_kb:
        print("Successfully rebuilt Knowledge Base FAISS index!")
    else:
        print("Knowledge Base is empty, nothing to build.")
        
    print("\nRebuilding User Uploads FAISS indexes...")
    users = db.query(User).all()
    for user in users:
        print(f"Checking user {user.email} (id={user.id})...")
        vs_user = rebuild_user_index(db, user.id)
        if vs_user:
            print(f"Successfully rebuilt FAISS index for user {user.email}!")
        else:
            print(f"No uploads found for user {user.email}.")
            
    db.close()
    print("\nAll FAISS indexes rebuilt successfully!")

if __name__ == "__main__":
    main()
