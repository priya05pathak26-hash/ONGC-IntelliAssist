import asyncio
import os
import sys
from sqlalchemy.orm import Session

sys.path.insert(0, os.getcwd())

# Ensure we are in backend dir
from app.database import SessionLocal
from app.services.documents import search_kb_documents

async def main():
    db = SessionLocal()
    question = "What is the Integrated Digital Analytics System (IDAS)"
    
    print("Testing search_kb_documents with query:", question)
    res = search_kb_documents(db, question, threshold=0.15)
    
    if res is None:
        print("No match found.")
    else:
        print("\n=== Result Found ===")
        print("Best Score:", res["score"])
        print("Best File:", res["file_name"])
        print("Best Page:", res["page_number"])
        print("\n--- Source Documents ---")
        for src in res["source_documents"]:
            print(f"File: {src['file_name']}, Page: {src['page_number']}, Score: {src['score']}")
        
        print("\n--- Chunk Context passed to LLM ---")
        # Write to utf-8 stdout
        sys.stdout.buffer.write(res["chunk"].encode('utf-8'))
        print()
        
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
