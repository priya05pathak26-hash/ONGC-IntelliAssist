import hashlib
import re
import shutil
import numpy as np
from sqlalchemy.orm import Session
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

from app.config import get_settings


_VECTORSTORE_CACHE: dict[str, FAISS] = {}

class LocalHashingEmbeddings(Embeddings):
    def __init__(self, dimension: int = 16384):
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        from app.services.text_tools import STOPWORDS
        # Split text into tokens, lowercased, and filter out common stopwords
        tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9_+-]+", text) if len(t) > 1]
        tokens = [t for t in tokens if t not in STOPWORDS]
        vec = np.zeros(self.dimension, dtype=np.float32)
        if not tokens:
            return vec.tolist()
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        return [self._embed(doc) for doc in documents]

    def embed_query(self, query: str) -> list[float]:
        return self._embed(query)


def _doc_total_pages(db, doc_id):
    from app.models import DocumentChunk
    from sqlalchemy import func
    result = (
        db.query(func.max(DocumentChunk.page_number))
        .filter(DocumentChunk.document_id == doc_id)
        .scalar()
    )
    return result or 0


def rebuild_kb_index(db: Session) -> FAISS | None:
    settings = get_settings()
    kb_path = settings.vector_db_dir / "knowledge_vectors"

    from app.models import Document, DocumentChunk
    kb_docs = db.query(Document).filter(Document.is_kb == True, Document.enabled == True).all()

    texts = []
    metadatas = []

    for doc in kb_docs:
        total_pages = _doc_total_pages(db, doc.id)
        doc_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        upload_time = doc.created_at.isoformat() if doc.created_at else None
        for chunk in doc_chunks:
            texts.append(chunk.text)
            metadatas.append({
                "document_id": doc.id,
                "file_name": doc.filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "chunk_number": chunk.chunk_index,
                "upload_time": upload_time,
                "document_type": "knowledge_base",
                "source": "Permanent Knowledge Base",
                "total_pages": total_pages,
                "created_by": doc.uploaded_by_id or "admin",
            })

    _VECTORSTORE_CACHE.pop(str(kb_path), None)
    if not texts:
        return None

    embeddings = LocalHashingEmbeddings()
    vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    kb_path.parent.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(kb_path))
    _VECTORSTORE_CACHE[str(kb_path)] = vectorstore
    return vectorstore


def rebuild_user_index(db: Session, user_id: int) -> FAISS | None:
    settings = get_settings()
    user_path = settings.vector_db_dir / "upload_vectors" / f"user_{user_id}"

    from app.models import Document, DocumentChunk
    user_docs = db.query(Document).filter(
        Document.uploaded_by_id == user_id,
        Document.is_kb == False,
        Document.enabled == True
    ).all()

    texts = []
    metadatas = []

    for doc in user_docs:
        total_pages = _doc_total_pages(db, doc.id)
        doc_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        upload_time = doc.created_at.isoformat() if doc.created_at else None
        for chunk in doc_chunks:
            texts.append(chunk.text)
            metadatas.append({
                "document_id": doc.id,
                "file_name": doc.filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "chunk_number": chunk.chunk_index,
                "upload_time": upload_time,
                "document_type": "user_upload",
                "source": "User Uploaded PDF",
                "total_pages": total_pages,
                "created_by": doc.uploaded_by_id or user_id,
            })

    _VECTORSTORE_CACHE.pop(str(user_path), None)
    if not texts:
        return None

    embeddings = LocalHashingEmbeddings()
    vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    user_path.parent.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(user_path))
    _VECTORSTORE_CACHE[str(user_path)] = vectorstore
    return vectorstore


def add_document_to_index(
    document_id: int,
    chunks: list[dict],
    *,
    is_kb: bool,
    user_id: int | None = None,
    upload_time: str | None = None,
    total_pages: int = 0,
    created_by: str | int | None = None,
    file_name: str | None = None,
) -> None:
    """Append a newly indexed document without recreating existing embeddings."""
    settings = get_settings()
    index_path = settings.vector_db_dir / "knowledge_vectors" if is_kb else settings.vector_db_dir / "upload_vectors" / f"user_{user_id}"
    if not chunks:
        return
    vectorstore = _VECTORSTORE_CACHE.get(str(index_path))
    if vectorstore is None:
        vectorstore = get_kb_vectorstore() if is_kb else get_user_vectorstore(user_id or 0)
    doc_type = "knowledge_base" if is_kb else "user_upload"
    src_label = "Permanent Knowledge Base" if is_kb else "User Uploaded PDF"
    owner = created_by if created_by is not None else ("admin" if is_kb else user_id)
    texts = [chunk["text"] for chunk in chunks]
    metadata = [{
        "document_id": document_id,
        "file_name": chunk.get("file_name") or file_name,
        "page_number": chunk.get("page_number"),
        "chunk_index": chunk.get("chunk_index"),
        "chunk_number": chunk.get("chunk_index"),
        "upload_time": upload_time,
        "document_type": doc_type,
        "source": src_label,
        "total_pages": total_pages,
        "created_by": owner,
    } for chunk in chunks]
    if vectorstore is None:
        vectorstore = FAISS.from_texts(texts, LocalHashingEmbeddings(), metadatas=metadata)
    else:
        vectorstore.add_texts(texts, metadatas=metadata)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(index_path))
    _VECTORSTORE_CACHE[str(index_path)] = vectorstore


def get_kb_vectorstore() -> FAISS | None:
    settings = get_settings()
    kb_path = settings.vector_db_dir / "knowledge_vectors"
    if not kb_path.exists() or not (kb_path / "index.faiss").exists():
        return None
    if str(kb_path) in _VECTORSTORE_CACHE:
        return _VECTORSTORE_CACHE[str(kb_path)]
    embeddings = LocalHashingEmbeddings()
    vectorstore = FAISS.load_local(str(kb_path), embeddings, allow_dangerous_deserialization=True)
    _VECTORSTORE_CACHE[str(kb_path)] = vectorstore
    return vectorstore


def get_user_vectorstore(user_id: int) -> FAISS | None:
    settings = get_settings()
    user_path = settings.vector_db_dir / "upload_vectors" / f"user_{user_id}"
    if not user_path.exists() or not (user_path / "index.faiss").exists():
        return None
    if str(user_path) in _VECTORSTORE_CACHE:
        return _VECTORSTORE_CACHE[str(user_path)]
    embeddings = LocalHashingEmbeddings()
    vectorstore = FAISS.load_local(str(user_path), embeddings, allow_dangerous_deserialization=True)
    _VECTORSTORE_CACHE[str(user_path)] = vectorstore
    return vectorstore
