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
        # Find the document
        doc = db.query(Document).filter(Document.filename.ilike("%ar2023-24.pdf%")).first()
        if not doc:
            print("ar2023-24.pdf not found in DB.")
            # Let's list all documents
            for d in db.query(Document).all():
                print(f"ID={d.id}, Filename={d.filename}, is_kb={d.is_kb}")
            return
        
        print(f"Found Doc ID={doc.id}, Filename={doc.filename}")
        
        # Query chunks for page 612 and 613
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id,
            DocumentChunk.page_number.in_([612, 613])
        ).all()
        
        for c in chunks:
            print(f"\n--- Page {c.page_number} Chunk {c.chunk_index} ---")
            print(c.text[:500])
            print("...")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
