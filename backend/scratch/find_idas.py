import sqlite3
import os

db_path = "c:/projects/ONGC_RAG_CHATBOT_NEW/ONGC_RAG_CHATBOT_NEW/backend/ongc_intelliassist.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, document_id, page_number, text FROM document_chunks WHERE text LIKE '%IDAS%' OR text LIKE '%Integrated Digital Analytics%' LIMIT 10")
chunks = cursor.fetchall()
print("IDAS matches:")
for chunk in chunks:
    print(f"Doc: {chunk[1]}, Page: {chunk[2]}, Text: {chunk[3][:250]}...")
conn.close()
