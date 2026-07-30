import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('backend/ongc_intelliassist.db')
cursor = conn.cursor()
cursor.execute("SELECT page_number, text FROM document_chunks WHERE document_id = 5 AND text LIKE '%1,378,463%'")
res = cursor.fetchall()
for page_num, text in res:
    print(f"Page: {page_num}")
    for line in text.split('\n'):
        if '1,378,463' in line:
            print(f"  {line[:200]}")
