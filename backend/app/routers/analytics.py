from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Document, Feedback, User, ChatSession, ChatMessage
from app.security import get_current_user


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def analytics(
    session_id: int | None = None,
    include_routing: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_chats = db.query(ChatSession).filter(ChatSession.user_id == user.id).count()
    questions_asked = db.query(ChatMessage).join(ChatSession).filter(ChatSession.user_id == user.id, ChatMessage.role == "user").count()
    questions_answered = db.query(ChatMessage).join(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatMessage.role == "assistant",
        ChatMessage.content != "",
        ChatMessage.source.isnot(None),
        ChatMessage.domain != "Error",
    ).count()
    avg_response_time = db.query(func.avg(ChatMessage.response_time_ms)).join(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatMessage.role == "assistant",
        ChatMessage.content != "",
        ChatMessage.domain != "Error",
    ).scalar() or 0
    uploaded_docs = db.query(Document).filter(Document.uploaded_by_id == user.id).count()
    session_messages = 0
    if session_id:
        selected = db.get(ChatSession, session_id)
        if selected and selected.user_id == user.id:
            session_messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
    
    rag_queries = db.query(ChatMessage).join(ChatSession).filter(
        ChatSession.user_id == user.id, 
        ChatMessage.role == "assistant", 
        ChatMessage.source == "Uploaded Documents"
    ).count()
    
    kb_queries = db.query(ChatMessage).join(ChatSession).filter(
        ChatSession.user_id == user.id, 
        ChatMessage.role == "assistant", 
        ChatMessage.source.in_(["Enterprise Knowledge Base", "ONGC Knowledge Base", "Built-in ONGC Enterprise Knowledge Base"])
    ).count()
    
    no_context_queries = db.query(ChatMessage).join(ChatSession).filter(
        ChatSession.user_id == user.id, 
        ChatMessage.role == "assistant", 
        ChatMessage.source == "No Relevant Context"
    ).count()
    
    helpful = db.query(Feedback).join(ChatMessage).join(ChatSession).filter(ChatSession.user_id == user.id, Feedback.helpful.is_(True)).count()
    not_helpful = db.query(Feedback).join(ChatMessage).join(ChatSession).filter(ChatSession.user_id == user.id, Feedback.helpful.is_(False)).count()
    
    domains = db.query(ChatMessage.domain, func.count(ChatMessage.id)).join(ChatSession).filter(
        ChatSession.user_id == user.id, 
        ChatMessage.role == "user"
    ).group_by(ChatMessage.domain).order_by(func.count(ChatMessage.id).desc()).limit(5).all()
    
    payload = {
        "total_questions": questions_answered,
        "questions_asked": questions_asked,
        "ai_responses": 0,
        "rag_responses": rag_queries,
        "knowledge_base_responses": kb_queries,
        "no_context_responses": no_context_queries,
        "average_response_time_ms": round(avg_response_time, 2),
        "feedback_ratio": {"helpful": helpful, "not_helpful": not_helpful},
        "most_active_domains": [{"domain": domain or "General", "count": count} for domain, count in domains],
        "most_uploaded_documents": uploaded_docs,
        
        "total_chats": total_chats,
        "questions_answered": questions_answered,
        "uploaded_documents": uploaded_docs,
        "rag_queries": rag_queries,
        "kb_queries": kb_queries,
        "fallback_queries": 0,
        "no_context_queries": no_context_queries,
        "current_session_messages": session_messages,
        "is_admin": user.role == "admin",
    }

    if user.role == "admin":
        payload["total_users"] = db.query(User).count()
        payload["admin_total_questions"] = db.query(ChatMessage).filter(ChatMessage.role == "user").count()

    if include_routing:
        selected_session = db.get(ChatSession, session_id) if session_id else None
        latest = None
        if selected_session and selected_session.user_id == user.id:
            latest = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == selected_session.id, ChatMessage.role == "assistant")
                .order_by(ChatMessage.created_at.desc())
                .first()
            )
        payload["active_document"] = "Focus only"
        payload["current_retrieval_source"] = latest.source if latest and latest.source else "None"

    return payload
