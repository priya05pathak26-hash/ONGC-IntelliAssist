import sqlite3
import os
import sys
import numpy as np
import hashlib
import re

sys.path.insert(0, os.getcwd())
from app.services.text_tools import STOPWORDS

db_path = "c:/projects/ONGC_RAG_CHATBOT_NEW/ONGC_RAG_CHATBOT_NEW/backend/ongc_intelliassist.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT page_number, text FROM document_chunks WHERE document_id = 3")
chunks = cursor.fetchall()

def embed_with_stopwords_filtered(text, dimension=512):
    tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9_+-]+", text) if len(t) > 1]
    tokens = [t for t in tokens if t not in STOPWORDS]
    vec = np.zeros(dimension, dtype=np.float32)
    if not tokens:
        return vec
    for token in tokens:
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dimension
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec

query = "what is carbon management policies"
q_emb = embed_with_stopwords_filtered(query)

scores = []
for page, text in chunks:
    c_emb = embed_with_stopwords_filtered(text)
    sim = np.dot(q_emb, c_emb)
    scores.append((page, sim, text))

scores.sort(key=lambda x: x[1], reverse=True)
print("Top 15 page chunk matches after filtering STOPWORDS:")
for page, sim, text in scores[:15]:
    print(f"Page: {page}, Sim: {sim:.4f}, Text: {text[:150]}...")

conn.close()
