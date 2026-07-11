import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatMessage, ChatSession, Feedback, User
from app.schemas import ChatRequest, ChatResponse, FeedbackIn, MessageOut, SessionOut
from app.security import get_current_user
from app.services.chat import answer_question, stream_answer_question


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    generator = stream_answer_question(db, user, payload.question, payload.session_id, payload.mode, payload.focus_document_id)
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return StreamingResponse(
        stream_answer_question(db, user, payload.question, payload.session_id, payload.mode, payload.focus_document_id),
        media_type="application/x-ndjson",
    )


@router.get("/sessions", response_model=list[SessionOut])
def sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(ChatSession).filter(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc()).all()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def messages(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat not found")
    rows = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    for row in rows:
        row.citations = json.loads(row.citations) if row.citations else None
    return rows


@router.patch("/sessions/{session_id}")
def rename(session_id: int, title: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat not found")
    session.title = title[:255]
    db.commit()
    return {"message": "Chat renamed"}


@router.patch("/sessions/{session_id}/pin")
def toggle_pin(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat not found")
    session.pinned = not session.pinned
    db.commit()
    return {"message": "Chat pin status updated", "pinned": session.pinned}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.delete(session)
    db.commit()
    return {"message": "Chat deleted"}


@router.post("/feedback")
def feedback(payload: FeedbackIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = db.get(ChatMessage, payload.message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    db.add(Feedback(message_id=payload.message_id, user_id=user.id, helpful=payload.helpful, comment=payload.comment))
    db.commit()
    return {"message": "Feedback recorded"}
