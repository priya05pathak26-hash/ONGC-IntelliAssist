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
cursor.execute("SELECT page_number, text FROM document_chunks WHERE document_id = 3 AND (page_number = 3 OR page_number = 7 OR page_number = 10 OR page_number = 426)")
chunks = cursor.fetchall()

embedder = LocalHashingEmbeddings()
query = "what is carbon management policies"
q_emb = embedder.embed_query(query)

print("For query:", query)
for page, text in chunks:
    c_emb = embedder.embed_query(text)
    sim = np.dot(q_emb, c_emb)
    print(f"Page {page} (sim={sim:.4f}): {text[:250]}...")

conn.close()
