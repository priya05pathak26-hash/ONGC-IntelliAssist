import sys
import os
sys.path.insert(0, os.getcwd())

import hashlib
import re
import numpy as np
import sqlite3

db_path = "c:/projects/ONGC_RAG_CHATBOT_NEW/ONGC_RAG_CHATBOT_NEW/backend/ongc_intelliassist.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get chunk from Page 104 of Doc 3
cursor.execute("SELECT text FROM document_chunks WHERE document_id = 3 AND page_number = 104 LIMIT 1")
text_104 = cursor.fetchone()[0]

# Query
query = "What is the Integrated Digital Analytics System (IDAS)"

dimension = 512
from app.services.text_tools import STOPWORDS

def _embed(text: str) -> list[float]:
    tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9_+-]+", text) if len(t) > 1]
    tokens = [t for t in tokens if t not in STOPWORDS]
    print(f"Text: {text[:100]}... -> Tokens: {tokens}")
    vec = np.zeros(dimension, dtype=np.float32)
    if not tokens:
        return vec.tolist()
    for token in tokens:
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dimension
        vec[idx] += 1.0
        print(f"  Token: {token} -> Hash: {h} -> Idx: {idx}")
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

vec_query = _embed(query)
vec_104 = _embed(text_104)

sim = np.dot(vec_query, vec_104)
print(f"Cosine Similarity: {sim}")

conn.close()
