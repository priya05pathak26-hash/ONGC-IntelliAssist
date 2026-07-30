from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Document, User, DocumentChunk
from app.security import get_current_user, require_admin
from app.services.chat import clear_response_cache
from app.services.documents import save_and_index_upload, get_kb_stats, get_document_metadata

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("")
async def upload(
    files: list[UploadFile],
    is_kb: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if is_kb and user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to upload Knowledge Base documents")
        
    indexed = []
    for file in files:
        document = await save_and_index_upload(db, file, user, is_kb=is_kb)
        indexed.append({"id": document.id, "filename": document.filename, "status": document.status})
    clear_response_cache()
    return {"documents": indexed}


@router.get("")
def list_documents(is_kb: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if is_kb:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required to view Knowledge Base documents")
        return db.query(Document).filter(Document.is_kb == True).order_by(Document.created_at.desc()).all()
    return db.query(Document).filter(Document.uploaded_by_id == user.id, Document.is_kb == False).order_by(Document.created_at.desc()).all()


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.is_kb:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required to delete Knowledge Base documents")
    else:
        if document.uploaded_by_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")
            
    settings = get_settings()
    suffix = Path(document.filename).suffix.lower()
    target_dir = settings.knowledge_base_dir if document.is_kb else settings.upload_dir
    file_path = target_dir / f"{document.content_hash}{suffix}"
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass
        
    db.delete(document)
    db.commit()
    
    # Rebuild corresponding vector index
    from app.services.vector_db import rebuild_kb_index, rebuild_user_index
    if document.is_kb:
        rebuild_kb_index(db)
    else:
        rebuild_user_index(db, user.id)
        
    clear_response_cache()
    return {"message": "Document deleted"}


@router.patch("/{document_id}/toggle")
def toggle_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.is_kb:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required to toggle Knowledge Base documents")
    else:
        if document.uploaded_by_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to toggle this document")
            
    document.enabled = not document.enabled
    db.commit()
    
    # Rebuild corresponding vector index
    from app.services.vector_db import rebuild_kb_index, rebuild_user_index
    if document.is_kb:
        rebuild_kb_index(db)
    else:
        rebuild_user_index(db, user.id)
        
    clear_response_cache()
    return {"id": document.id, "enabled": document.enabled}


@router.post("/{document_id}/reindex")
def reindex_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.is_kb:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required to reindex Knowledge Base documents")
    else:
        if document.uploaded_by_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to reindex this document")

    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()

    settings = get_settings()
    suffix = Path(document.filename).suffix.lower()
    target_dir = settings.knowledge_base_dir if document.is_kb else settings.upload_dir
    stored_path = target_dir / f"{document.content_hash}{suffix}"

    if not stored_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found")

    from app.services.extractors import extract_text
    from app.services.text_tools import chunk_text, embedding
    import json
    from app.services.vector_db import add_document_to_index

    all_pages = list(extract_text(stored_path))
    non_empty_pages = [(p, t) for (p, t) in all_pages if t and str(t).strip()]

    chunk_index = 0
    indexed_chunks = []
    for page_number, text in non_empty_pages:
        for chunk in chunk_text(text):
            chunk_index += 1
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    text=chunk,
                    embedding=json.dumps(embedding(chunk)),
                )
            )
            indexed_chunks.append({
                "text": chunk,
                "file_name": document.filename,
                "page_number": page_number,
                "chunk_index": chunk_index,
            })

    document.status = "indexed"
    db.commit()

    from app.services.vector_db import rebuild_kb_index, rebuild_user_index
    if document.is_kb:
        rebuild_kb_index(db)
    else:
        rebuild_user_index(db, user.id)

    clear_response_cache()
    return {"message": "Document re-indexed successfully", "total_chunks": chunk_index}


@router.get("/kb/stats")
def kb_statistics(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    stats = get_kb_stats(db)
    return stats


@router.get("/{document_id}/metadata")
def document_metadata(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.is_kb:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required to view Knowledge Base metadata")
    else:
        if document.uploaded_by_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this document's metadata")
    meta = get_document_metadata(db, document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return meta


@router.get("/kb/summaries")
def kb_summaries(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import or_
    query = db.query(Document).filter(Document.is_kb == True)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.filter(or_(Document.filename.ilike(like), Document.summary.ilike(like)))
    docs = query.order_by(Document.created_at.desc()).all()
    payload = []
    for doc in docs:
        total_chunks = (
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
        )
        total_pages = (
            db.query(DocumentChunk.page_number)
            .filter(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.page_number.desc())
            .first()
        )
        payload.append({
            "id": doc.id,
            "filename": doc.filename,
            "size_bytes": doc.size_bytes,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "status": doc.status,
            "enabled": doc.enabled,
            "is_kb": True,
            "summary": doc.summary,
            "total_chunks": total_chunks,
            "total_pages": total_pages[0] if total_pages and total_pages[0] else 0,
            "embedding_status": "Completed" if doc.status == "indexed" and total_chunks > 0 else "Pending",
            "indexed_status": "Indexed" if doc.status == "indexed" and total_chunks > 0 else "Not Indexed",
            "document_type": "knowledge_base",
            "uploaded_by_id": doc.uploaded_by_id,
        })
    return payload
