import sqlite3
import os

db_path = "c:/projects/ONGC_RAG_CHATBOT_NEW/ONGC_RAG_CHATBOT_NEW/backend/ongc_intelliassist.db"
if not os.path.exists(db_path):
    print("Database not found at path:", db_path)
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename FROM documents")
    docs = cursor.fetchall()
    print("Documents:")
    for doc in docs:
        print(doc)
    
    cursor.execute("SELECT id, document_id, page_number, text FROM document_chunks WHERE text LIKE '%carbon%' LIMIT 10")
    chunks = cursor.fetchall()
    print("\nChunks matching 'carbon':")
    for chunk in chunks:
        print(f"Doc ID: {chunk[1]}, Page: {chunk[2]}, Text: {chunk[3][:200]}...")
    conn.close()
