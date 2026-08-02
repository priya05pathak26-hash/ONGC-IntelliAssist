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
cursor.execute("SELECT page_number, text FROM document_chunks WHERE document_id = 3")
chunks = cursor.fetchall()

embedder = LocalHashingEmbeddings()

# Test expanded query
query = "what is carbon management policies carbon neutrality net-zero scope-1 scope-2 emissions greenhouse gas co2 sustainability climate"
q_emb = embedder.embed_query(query)

scores = []
for page, text in chunks:
    c_emb = embedder.embed_query(text)
    sim = np.dot(q_emb, c_emb)
    scores.append((page, sim, text))

scores.sort(key=lambda x: x[1], reverse=True)
print("Top 15 page chunk matches with query expansion:")
for page, sim, text in scores[:15]:
    print(f"Page: {page}, Sim: {sim:.4f}, Text: {text[:150]}...")

conn.close()
