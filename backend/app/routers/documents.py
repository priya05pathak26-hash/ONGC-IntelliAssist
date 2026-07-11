from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Document, User
from app.security import get_current_user
from app.services.chat import clear_response_cache
from app.services.documents import save_and_index_upload, DocumentVectorCache


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("")
async def upload(files: list[UploadFile], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    indexed = []
    for file in files:
        document = await save_and_index_upload(db, file, user)
        indexed.append({"id": document.id, "filename": document.filename, "status": document.status})
    clear_response_cache()
    return {"documents": indexed}


@router.get("")
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Document).filter(Document.uploaded_by_id == user.id).order_by(Document.created_at.desc()).all()


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if document and document.uploaded_by_id == user.id:
        settings = get_settings()
        suffix = Path(document.filename).suffix.lower()
        file_path = settings.upload_dir / f"{document.content_hash}{suffix}"
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
        db.delete(document)
        db.commit()
        DocumentVectorCache.refresh(db, user.id)
        clear_response_cache()
    return {"message": "Document deleted"}

@router.patch("/{document_id}/toggle")
def toggle_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if not document or document.uploaded_by_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    # Toggle enabled flag
    document.enabled = not document.enabled
    db.commit()
    DocumentVectorCache.refresh(db, user.id)
    clear_response_cache()
    return {"id": document.id, "enabled": document.enabled}
