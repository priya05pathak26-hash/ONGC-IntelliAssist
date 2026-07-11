import json
import httpx
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Document, DocumentChunk, User
from app.services.extractors import extract_text
from app.services.text_tools import chunk_text, cosine, embedding, stable_hash
# ----------------------------------------------------------------------
# Summary generation (Ollama)
# ----------------------------------------------------------------------
async def generate_summary(document_id: int, db: Session) -> str:
    """
    Create a concise summary for a document using the local Ollama server.

    Steps:
    1. Pull a limited number of chunks (e.g., first 20) to keep the prompt short.
    2. Concatenate their text.
    3. Send a prompt to Ollama's `/api/generate` endpoint.
    4. Return the generated summary or an empty string on failure.
    """
    # Gather some text from the document
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .limit(20)
        .all()
    )
    text_blob = " ".join(chunk.text for chunk in chunks)
    if not text_blob:
        return ""

    prompt = (
        "Summarize the following document in a concise paragraph suitable for a "
        "knowledge‑card UI. Do not add information that is not present in the text.\n\n"
        f"{text_blob}"
    )

    try:
        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception:
        # Silently ignore summarisation failures – the upload will still succeed.
        return ""


settings = get_settings()


class DocumentVectorCache:
    _cached_chunks: dict[int, list[dict]] = {}

    @classmethod
    def get_chunks(cls, db: Session, user_id: int):
        if user_id not in cls._cached_chunks:
            cls.refresh(db, user_id)
        return cls._cached_chunks[user_id]

    @classmethod
    def refresh(cls, db: Session, user_id: int | None = None):
        if user_id is None:
            cls._cached_chunks.clear()
            return
        chunks = db.query(DocumentChunk).join(Document).filter(Document.uploaded_by_id == user_id).all()
        cls._cached_chunks[user_id] = []
        for chunk in chunks:
            try:
                emb = json.loads(chunk.embedding)
            except Exception:
                emb = {}
            cls._cached_chunks[user_id].append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "file_name": chunk.document.filename,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "embedding": emb,
                "enabled": chunk.document.enabled
            })


async def save_and_index_upload(db: Session, file: UploadFile, user: User) -> Document:
    raw = await file.read()
    max_size = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_size:
        raise HTTPException(status_code=413, detail="Maximum upload size is 100 MB")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported")
    digest = stable_hash(f"{user.id}:".encode() + raw)
    existing = db.query(Document).filter(Document.content_hash == digest, Document.uploaded_by_id == user.id).first()
    if existing:
        return existing
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = settings.upload_dir / f"{digest}{suffix}"
    stored_path.write_bytes(raw)
    document = Document(
        filename=file.filename or stored_path.name,
        content_hash=digest,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(raw),
        uploaded_by_id=user.id,
    )
    db.add(document)
    db.flush()
    chunk_index = 0
    for page_number, text in extract_text(stored_path):
        for chunk in chunk_text(text):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    text=chunk,
                    embedding=json.dumps(embedding(chunk)),
                )
            )
            chunk_index += 1
    db.commit()
    db.refresh(document)
    # Generate AI summary for the uploaded document
    try:
        summary = await generate_summary(document.id, db)
        document.summary = summary
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception:
        # If summarization fails, continue without summary
        pass
    DocumentVectorCache.refresh(db, user.id)
    return document


def search_uploaded_documents(db: Session, user: User, question: str, threshold: float = 0.31, document_id: int | None = None) -> dict | None:
    query_embedding = embedding(question)
    cached = DocumentVectorCache.get_chunks(db, user.id)
    if not cached:
        return None
        
    scored_chunks = []
    for chunk in cached:
        # Skip disabled documents
        if not chunk.get("enabled", True):
            continue
        if document_id is not None and chunk["document_id"] != document_id:
            continue
        score = cosine(query_embedding, chunk["embedding"])
        scored_chunks.append((score, chunk))
        
    if not scored_chunks:
        return None
        
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    best_score, best_chunk = scored_chunks[0]
    
    if best_score < threshold:
        return None
        
    best_doc_id = best_chunk["document_id"]
    best_doc_name = best_chunk["file_name"]
    
    # Isolate chunks belonging to the most relevant document
    doc_scored_chunks = [x for x in scored_chunks if x[1]["document_id"] == best_doc_id]
    
    # Retrieve top 3 chunks for this document
    top_chunks = doc_scored_chunks[:3]
    
    # Combine their contexts without exposing raw chunk separators to the UI.
    combined_context = "\n\n".join(item[1]["text"].strip() for item in top_chunks if item[1]["text"].strip())
    
    return {
        "score": best_score,
        "chunk": combined_context,
        "page_number": best_chunk["page_number"],
        "file_name": best_doc_name,
        "document_id": best_doc_id,
        "top_chunks": [
            {
                "page_number": item[1]["page_number"],
                "score": round(item[0], 4),
            } for item in top_chunks
        ],
    }
