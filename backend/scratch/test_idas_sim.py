import sqlite3
import os
import sys
import numpy as np
import hashlib
import re

sys.path.insert(0, os.getcwd())
from app.services.vector_db import LocalHashingEmbeddings

db_path = "c:/projects/ONGC_RAG_CHATBOT_NEW/ONGC_RAG_CHATBOT_NEW/backend/ongc_intelliassist.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, document_id, page_number, text FROM document_chunks WHERE text LIKE '%IDAS%' OR text LIKE '%Integrated Digital Analytics%'")
chunks = cursor.fetchall()

embedder = LocalHashingEmbeddings()
query = "What is the Integrated Digital Analytics System (IDAS)"
q_emb = embedder.embed_query(query)

print("For query:", query)
for cid, doc_id, page, text in chunks:
    c_emb = embedder.embed_query(text)
    sim = np.dot(q_emb, c_emb)
    print(f"Doc {doc_id}, Page {page} (sim={sim:.4f}): {text[:200]}...")

conn.close()
