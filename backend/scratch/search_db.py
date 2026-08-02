import sys
from pathlib import Path
import json

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models import Document, DocumentChunk

def main():
    db = SessionLocal()
    try:
        # Search for "carbon" in all chunks
        print("--- Searching for chunks containing 'carbon' ---")
        chunks = db.query(DocumentChunk).filter(DocumentChunk.text.ilike("%carbon%")).limit(10).all()
        for c in chunks:
            print(f"Doc={c.document.filename}, Page={c.page_number}, Chunk={c.chunk_index}")
            print(c.text[:200])
            print("-" * 50)
            
        print("\n--- Searching for chunks containing 'net zero' ---")
        chunks_nz = db.query(DocumentChunk).filter(DocumentChunk.text.ilike("%net zero%")).limit(5).all()
        for c in chunks_nz:
            print(f"Doc={c.document.filename}, Page={c.page_number}, Chunk={c.chunk_index}")
            print(c.text[:200])
            print("-" * 50)
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
