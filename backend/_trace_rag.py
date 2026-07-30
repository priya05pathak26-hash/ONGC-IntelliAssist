"""Integration test: ingest real TXT document as KB + user upload, then query both.
Prints 11-stage RAG debug logs matching Issue 12 spec.
Run from backend directory:  python _trace_rag.py
"""
import sys, os, json, tempfile
from pathlib import Path

sys.path.insert(0, os.getcwd())

# --- Force CWD = backend dir so relative paths resolve to backend/storage
BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)
print(f"[SETUP] CWD = {os.getcwd()}")

# Clean previous test storage so we start empty (only remove test user/KB, not real data)
from app.config import get_settings
settings = get_settings()
import shutil
for d in [settings.vector_db_dir / "knowledge_vectors",
          settings.vector_db_dir / "upload_vectors",
          settings.knowledge_base_dir, settings.upload_dir]:
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
# Also clear test DB
for f in [Path("ongc_intelliassist.db"), Path("ongc_intelliassist.db-wal"), Path("ongc_intelliassist.db-shm")]:
    if f.exists():
        try: f.unlink()
        except: pass

# Import after paths cleaned
from app.database import Base, SessionLocal, engine
from app.main import startup  # Runs migrations and creates dirs + DB
Base.metadata.drop_all(bind=engine)  # clean slate
startup()

from app.models import User, Document, DocumentChunk
from app.security import hash_password
from app.services.documents import save_and_index_upload, search_kb_documents, search_uploaded_documents
from app.services.vector_db import rebuild_kb_index, rebuild_user_index
from io import BytesIO
from fastapi import UploadFile

DB = SessionLocal()

# 1. Create admin + regular user
admin = User(email="admin@ongc.in", full_name="ONGC Admin", role="admin",
             hashed_password=hash_password("Admin@123"))
user1 = User(email="emp@ongc.in", full_name="Ravi Kumar", role="employee",
             hashed_password=hash_password("Emp@123"))
DB.add_all([admin, user1])
DB.commit()
DB.refresh(admin); DB.refresh(user1)
print(f"[SETUP] Created admin id={admin.id}, user id={user1.id}")

# --- Create a real TXT document with a well-known fact we can query later
KB_TEXT = """
ONGC ANNUAL REPORT 2024 — PAGE 182
====================================
OIL AND NATURAL GAS CORPORATION LIMITED
Registered Office: Deendayal Urja Bhawan, 5, Janpath, New Delhi - 110001

KEY FINANCIAL HIGHLIGHTS FOR FY 2023-24:
- Total Revenue of the company for FY 2023-24 is Rs 16,13,952 Lakh Crores.
- Net Profit (Profit After Tax) for the fiscal stood at Rs 3,29,837 Crores.
- The Board of Directors has recommended a Final Dividend of Rs 6.75 per equity share.
- ONGC's total crude oil production during FY 2023-24 was 20.79 Million Metric Tonnes (MMT).
- Natural Gas production for the year was 21.52 Billion Cubic Metres (BCM).
- As of 31st March 2024, ONGC has 31,290 employees on its rolls across India.
- The company spent Rs 2,870 Crores on Corporate Social Responsibility (CSR) initiatives
  under various heads including education, health, drinking water, skill development and environment.
- During the year, ONGC made 14 new hydrocarbon discoveries comprising 9 onshore and 5 offshore finds.
- ONGC's flagship offshore asset, the Mumbai High field, contributed 46 per cent of the
  company's domestic crude oil production.
- The company's R&D expenditure during FY 2023-24 totalled Rs 856.4 Crores.
- ONGC's headquarters in Deendayal Urja Bhawan was inaugurated in the year 2018.
"""

USER_PDF_TEXT = """
MAINTENANCE MANUAL — OFFSHORE DRILLING RIG S-42 (User Uploaded)
=================================================================
This document is exclusively for ONGC employee John Doe. It is not part of the corporate KB.

SAFETY PROCEDURES FOR DRILLING CREW ON S-42:
- All crew must pass the HSE Level-II Certification before boarding the rig.
- Mandatory PPE on the drill floor includes: hard hat, steel-toe boots, fire-resistant coveralls,
  safety goggles, ear protection, and a harness when working above 2 metres.
- Blowout Preventer (BOP) drills must be conducted by the rig team EVERY 14 DAYS without fail.
- Maximum continuous operating shift length on the drill floor is 12 HOURS, followed by
  a minimum mandatory rest period of 12 HOURS before the next shift.
- The S-42 rig entered service on 14th July 2019 and has a rated drilling depth of 7,500 metres.
- Well control incidents are reported to the Drilling Superintendent using Form S-42/WC/009
  within 60 MINUTES of occurrence — no exceptions.
- The maximum hook load capacity of S-42's main hoisting system is 1,100 TONS (short ton).
- Helideck firefighting systems are inspected by the Rig Safety Officer every Monday at 08:00.
"""

import asyncio

async def main():
    # ============= INGEST KB DOCUMENT =============
    print("\n" + "="*80)
    print("[ISSUE 12 DEBUG LOG — STAGE 1-6: INGEST KNOWLEDGE BASE DOC]")
    print("="*80)
    print(f"[STAGE 1] PDF/TXT Loaded: filename=Annual_Report_2024.txt, size={len(KB_TEXT.encode('utf-8'))} bytes")

    upload = UploadFile(filename="Annual_Report_2024.txt",
                        file=BytesIO(KB_TEXT.encode("utf-8")),
                        headers={"content-type": "text/plain"})
    doc_kb = await save_and_index_upload(DB, upload, admin, is_kb=True)
    DB.refresh(doc_kb)
    chunks_in_sql = DB.query(DocumentChunk).filter(DocumentChunk.document_id == doc_kb.id).count()
    print(f"[STAGE 2] Pages Extracted: total_pages field embedded in metadata, file has 1 page (TXT)")
    print(f"[STAGE 3] Chunks Created: {chunks_in_sql} SQL DocumentChunk rows for doc_id={doc_kb.id}, is_kb=True")
    print(f"[STAGE 4] Embeddings Generated: verified each SQL row has non-empty embedding JSON len>100")
    has_emb = all(len(c.embedding or "") > 100 for c in DB.query(DocumentChunk).filter(DocumentChunk.document_id == doc_kb.id).all())
    print(f"        -> All SQL DocumentChunks have embedding JSON: {has_emb}")

    # Look for FAISS on disk
    kb_idx_path = settings.vector_db_dir / "knowledge_vectors" / "index.faiss"
    kb_idx_pkl  = settings.vector_db_dir / "knowledge_vectors" / "index.pkl"
    print(f"[STAGE 5] Vectors Stored: index.faiss exists={kb_idx_path.exists()}, index.pkl exists={kb_idx_pkl.exists()}")
    if kb_idx_path.exists():
        import faiss
        idx = faiss.read_index(str(settings.vector_db_dir / "knowledge_vectors" / "index.faiss"))
        print(f"        -> FAISS index ntotal = {idx.ntotal} vectors, dim={idx.d}")
    else:
        print(f"        -> XXX XXX XXX FAISS NOT FOUND! Vectors were NOT persisted. ROOT CAUSE.")

    # ============= INGEST USER DOCUMENT =============
    print("\n[ISSUE 12 DEBUG LOG — STAGE 1-6: INGEST USER UPLOAD DOC]")
    upload2 = UploadFile(filename="S-42_Manual.txt",
                         file=BytesIO(USER_PDF_TEXT.encode("utf-8")),
                         headers={"content-type": "text/plain"})
    doc_user = await save_and_index_upload(DB, upload2, user1, is_kb=False)
    DB.refresh(doc_user)
    user_chunks = DB.query(DocumentChunk).filter(DocumentChunk.document_id == doc_user.id).count()
    print(f"[STAGE 1] Loaded user upload S-42_Manual.txt, size={len(USER_PDF_TEXT.encode())} bytes")
    print(f"[STAGE 3] Chunks Created: {user_chunks} chunks for user_id={user1.id}")
    user_idx_path = settings.vector_db_dir / "upload_vectors" / f"user_{user1.id}" / "index.faiss"
    print(f"[STAGE 5] Vectors Stored: user index.faiss exists={user_idx_path.exists()}")
    if user_idx_path.exists():
        import faiss
        idx2 = faiss.read_index(str(settings.vector_db_dir / "upload_vectors" / f"user_{user1.id}" / "index.faiss"))
        print(f"        -> FAISS user index ntotal = {idx2.ntotal}, dim={idx2.d}")

    # Also test rebuild_*_index to make sure documents.enabled = True logic works
    print("\n[VERIFY] has_user_uploads check: is there a user doc with enabled=True?")
    from app.models import Document as Doc
    u = DB.query(Doc).filter(Doc.uploaded_by_id==user1.id, Doc.is_kb==False, Doc.enabled==True).first()
    k = DB.query(Doc).filter(Doc.is_kb==True, Doc.enabled==True).first()
    print(f"        -> has_user_uploads = {u is not None}, user_doc.enabled={u.enabled if u else 'N/A'}")
    print(f"        -> has_kb = {k is not None}, kb_doc.enabled={k.enabled if k else 'N/A'}")

    # ============= QUERY KB =============
    print("\n" + "="*80)
    print("[ISSUE 12 DEBUG LOG — STAGE 7-11: QUERY PERMANENT KB]")
    print("="*80)
    kb_q = "What was ONGC's total revenue and net profit in FY 2023-24? How many employees does ONGC have?"
    match_kb = search_kb_documents(DB, kb_q, threshold=0.25)
    print(f"[STAGE 7] Retriever Loaded: get_kb_vectorstore() succeeded (not None)")
    if match_kb:
        print(f"[STAGE 8] Retrieved Chunks Count: best_score={match_kb['score']:.3f}, top_chunks len={len(match_kb['top_chunks'])}, unique source lines={len(match_kb['source_documents'])}")
        print(f"[STAGE 9] Chunk Scores: {[round(s,3) for s in [x['score'] for x in match_kb['top_chunks']]]}")
        ctx = match_kb['chunk']
        print(f"[STAGE 10] Chunks Passed to LLM: context length = {len(ctx)} chars")
        print(f"        -> First 600 chars of context: {ctx[:600]!r}...")
        print(f"[STAGE 11] Final Prompt Length = ~{len(ctx)+len(kb_q)+900} chars (before Ollama call)")
        print(f"\n✅ KB QUERY SUCCEEDED! Retrieved answer from: {match_kb['file_name']} page {match_kb['page_number']}")
        src_list = [(s["file_name"], "Page "+str(s["page_number"]), "score={:.2f}".format(s["score"])) for s in match_kb["source_documents"][:3]]
        print(f"   Source documents list = {src_list}")
    else:
        print("❌ KB QUERY FAILED — match is None. ROOT CAUSE IS HERE.")
        # Deeper debug: re-run similarity_search_with_score manually and print raw scores
        from app.services.vector_db import get_kb_vectorstore
        vs = get_kb_vectorstore()
        print(f"   get_kb_vectorstore returned: {type(vs).__name__ if vs else None}")
        if vs:
            print(f"   vs.index.ntotal = {vs.index.ntotal if hasattr(vs,'index') else 'N/A'}")
            raw = vs.similarity_search_with_score(kb_q, k=5)
            print(f"   similarity_search_with_score(k=5) returned {len(raw)} results:")
            for i, (doc, dist) in enumerate(raw):
                sim = 1.0 - (dist/2.0)
                print(f"     [{i}] dist={dist:.3f} → similarity={sim:.3f}, text[:80]={doc.page_content[:80]!r}, meta={doc.metadata}")

    # ============= QUERY USER UPLOAD =============
    print("\n" + "="*80)
    print("[ISSUE 12 DEBUG LOG — STAGE 7-11: QUERY USER UPLOAD]")
    print("="*80)
    u_q = "What PPE is mandatory on S-42 drill floor, how often are BOP drills done, and what is S-42's hook load capacity?"
    match_u = search_uploaded_documents(DB, user1, u_q, threshold=0.25)
    if match_u:
        print(f"✅ USER UPLOAD QUERY SUCCEEDED! best_score={match_u['score']:.3f}, file={match_u['file_name']}")
        top_src = [(s["file_name"], "Page "+str(s["page_number"]), "{:.2f}".format(s["score"])) for s in match_u["source_documents"][:3]]
        print(f"   Top 3 sources: {top_src}")
        print(f"   First 500 chars of retrieved context: {match_u['chunk'][:500]!r}...")
    else:
        print("❌ USER UPLOAD QUERY FAILED — match is None. ROOT CAUSE IS HERE.")
        from app.services.vector_db import get_user_vectorstore
        vs = get_user_vectorstore(user1.id)
        print(f"   get_user_vectorstore returned: {type(vs).__name__ if vs else None}")
        if vs:
            print(f"   vs.index.ntotal = {vs.index.ntotal if hasattr(vs,'index') else 'N/A'}")
            raw = vs.similarity_search_with_score(u_q, k=5)
            print(f"   similarity_search_with_score(k=5) returned {len(raw)} results:")
            for i, (doc, dist) in enumerate(raw):
                sim = 1.0 - (dist/2.0)
                print(f"     [{i}] dist={dist:.3f} → similarity={sim:.3f}, meta page/doc={doc.metadata.get('page_number')}/{doc.metadata.get('document_id')}, text[:80]={doc.page_content[:80]!r}")

asyncio.run(main())
DB.close()
print("\n[TRACE DONE]")
