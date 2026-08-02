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

# Get all chunks from Page 9 of Doc 5
cursor.execute("SELECT text FROM document_chunks WHERE document_id = 5 AND page_number = 9")
chunks = cursor.fetchall()

query = "What is the Integrated Digital Analytics System (IDAS)"

from app.services.text_tools import STOPWORDS
dimension = 8192

def get_tokens(text):
    tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9_+-]+", text) if len(t) > 1]
    return [t for t in tokens if t not in STOPWORDS]

for idx, (text,) in enumerate(chunks):
    q_toks = get_tokens(query)
    p9_toks = get_tokens(text)
    
    # Calculate vector sim manually
    q_vec = np.zeros(dimension)
    for t in q_toks:
        i = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % dimension
        q_vec[i] += 1.0

    p9_vec = np.zeros(dimension)
    for t in p9_toks:
        i = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % dimension
        p9_vec[i] += 1.0

    q_norm = np.linalg.norm(q_vec)
    p9_norm = np.linalg.norm(p9_vec)
    dot = np.dot(q_vec, p9_vec)
    sim = dot / (q_norm * p9_norm)
    
    print("\nChunk {}:".format(idx))
    print("  Text:", text[:150] + "...")
    print("  Matches:", [t for t in q_toks if t in p9_toks])
    print("  Sim:", sim)

conn.close()
