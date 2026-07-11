"""
Chat routing pipeline for ONGC intelliAssist.

The backend classifies intent before retrieval. Uploaded documents are used
only for explicit document questions or explicit Focus Mode requests.
"""

import asyncio
import datetime
import json
import re
import time
from collections.abc import AsyncIterator

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog, ChatMessage, ChatSession, User
from app.services.documents import search_uploaded_documents
from app.services.intents import IntentCategory, classify_intent
from app.services.kb import search_knowledge

settings = get_settings()


SOURCE_GENERAL = "General AI"
SOURCE_UPLOADS = "Uploaded Documents"
SOURCE_ONGC = "ONGC Knowledge Base"
SOURCE_ENTERPRISE = "Enterprise Knowledge Base"


_RESPONSE_CACHE = {}

def clear_response_cache():
    _RESPONSE_CACHE.clear()

def _clean_question(question: str) -> str:
    return " ".join(question.split()).strip()


def _trim_context(context: str, max_chars: int = 2000) -> str:
    text = re.sub(r"\s+", " ", context or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def _history_text(history: list[ChatMessage]) -> str:
    lines = []
    for msg in history[-6:]:
        role = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def _generate_chat_title(question: str) -> str:
    q = question.strip().lower()
    q = re.sub(r"[^\w\s.-]", "", q)
    prefixes = [
        r"^what is a\b", r"^what is\b", r"^what are the\b", r"^what are\b", r"^explain the\b", r"^explain\b",
        r"^how does\b", r"^how to\b", r"^summarize the\b", r"^summarize\b", r"^tell me about\b", r"^about\b"
    ]
    for pat in prefixes:
        q = re.sub(pat, "", q).strip()
    
    pdf_match = re.search(r"([\w -]+)\.pdf", question, re.IGNORECASE)
    if pdf_match:
        base = pdf_match.group(1).strip()
        return f"{base.title()} Summary"

    if "leave policy" in q:
        return "HR Leave Policy"
    if "reservoir engineering" in q:
        return "Reservoir Engineering"
    if "procurement workflow" in q or "procurement process" in q:
        return "Procurement Workflow"
    if "biology chapter" in q:
        return "Biology Summary"

    words = q.split()
    if not words:
        return "New Chat"
    
    title_str = " ".join(words[:4])
    if title_str == "ppe":
        return "PPE Guidelines"
    if title_str == "ptw":
        return "PTW Guidelines"
    if title_str in ("procurement", "procurement process"):
        return "Procurement Process"
    if title_str == "hse":
        return "HSE Guidelines"
    
    return title_str.title()


def _build_general_prompt(question: str, history: list[ChatMessage]) -> str:
    return (
        "You are ONGC IntelliAssist, a helpful AI assistant.\n"
        "Answer directly in natural, complete language. Use short paragraphs and bullets only when helpful.\n"
        "Keep the answer concise for simple questions and detailed only when the user asks for detail.\n"
        "Do not mention routing, retrieval, hidden instructions, or internal systems.\n"
        "If the question asks for current facts and you are unsure, say that the answer may need verification.\n\n"
        f"Conversation:\n{_history_text(history)}\n\n"
        f"User question: {question}\n"
        "Assistant:"
    )


def _build_synthesis_prompt(question: str, context: str, source_label: str, history: list[ChatMessage]) -> str:
    return (
        "You are ONGC IntelliAssist, a helpful enterprise assistant.\n"
        "Use only the provided source material to answer the user's question.\n"
        "Write like ChatGPT: clear, complete, and easy to read.\n"
        "Do not concatenate raw text. Do not include OCR artifacts, chunk labels, scores, or '[Next Chunk]'.\n"
        "Do not begin with phrases like 'Based on', 'According to', or 'This is the most relevant information'.\n"
        "Do not create a 'Key Points' section unless the user explicitly asks for key points.\n"
        "Do not add a source note inside the answer body.\n"
        "If the source material is not enough, say that briefly and answer only what is supported.\n\n"
        f"Source material ({source_label}):\n{_trim_context(context)}\n\n"
        f"Conversation:\n{_history_text(history)}\n\n"
        f"User question: {question}\n"
        "Assistant:"
    )


async def _call_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                settings.ollama_url,
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
    except Exception:
        return ""


async def _general_ai_answer(question: str, history: list[ChatMessage]) -> str:
    prompt = _build_general_prompt(question, history)
    answer = await _call_ollama(prompt)
    return answer or "I could not reach the local AI model. Please make sure Ollama is running and try again."


async def _synthesize_answer(question: str, context: str, source_label: str, history: list[ChatMessage]) -> str:
    prompt = _build_synthesis_prompt(question, context, source_label, history)
    answer = await _call_ollama(prompt)
    return answer or "I found relevant material, but the local AI model could not generate a response right now."


def _source_citation(source: str, file_name: str | None = None, page_number: int | None = None, score: float | None = None) -> list[dict]:
    citation = {
        "source": source,
        "file_name": file_name,
        "page_number": page_number,
        "similarity_score": round(score, 4) if isinstance(score, (int, float)) else None,
        "retrieved_chunk": None,
    }
    return [citation]


async def _stream_ollama(prompt: str) -> AsyncIterator[str]:
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                settings.ollama_url,
                json={"model": settings.ollama_model, "prompt": prompt, "stream": True},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = payload.get("response", "")
                    if token:
                        yield token
                    if payload.get("done"):
                        break
    except Exception:
        yield "I could not reach the local AI model. Please make sure Ollama is running and try again."


def _event(event: str, **payload) -> str:
    return json.dumps({"event": event, **payload}, ensure_ascii=False) + "\n"


async def answer_question(
    db: Session,
    user: User,
    question: str,
    session_id: int | None,
    mode: str = "auto",
    focus_document_id: int | None = None,
) -> dict:
    started = time.perf_counter()
    clean_question = _clean_question(question)

    # In-memory response cache lookup
    cache_key = (user.id, clean_question, focus_document_id, mode)
    if cache_key in _RESPONSE_CACHE:
        cached = _RESPONSE_CACHE[cache_key]
        
        session = db.get(ChatSession, session_id) if session_id else None
        is_new_session = False
        if not session or session.user_id != user.id:
            session = ChatSession(user_id=user.id, title="New Chat")
            db.add(session)
            db.flush()
            is_new_session = True

        if is_new_session or session.title == "New Chat":
            session.title = _generate_chat_title(clean_question)

        user_message = ChatMessage(session_id=session.id, role="user", content=clean_question)
        db.add(user_message)
        db.flush()

        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=cached["answer"],
            source=cached["source"],
            domain=cached["domain"],
            similarity_score=cached["score"],
            response_time_ms=0,
            citations=json.dumps(cached["citations"], ensure_ascii=False),
        )
        session.updated_at = datetime.datetime.utcnow()
        db.add(assistant_message)
        db.add(
            AuditLog(
                user_id=user.id,
                question=clean_question,
                response=cached["answer"],
                domain=cached["domain"] or "General",
                source=cached["source"],
                similarity_score=cached["score"],
                response_time_ms=0,
            )
        )
        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)

        return {
            "session_id": session.id,
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
            "answer": cached["answer"],
            "source": cached["source"],
            "domain": cached["domain"],
            "response_time_ms": 0,
            "citations": cached["citations"],
        }

    session = db.get(ChatSession, session_id) if session_id else None
    is_new_session = False
    if not session or session.user_id != user.id:
        session = ChatSession(user_id=user.id, title="New Chat")
        db.add(session)
        db.flush()
        is_new_session = True

    # Never persist focus/routing state on the session. Focus is explicit per request.
    session.active_document_id = None
    session.active_source = None

    user_message = ChatMessage(session_id=session.id, role="user", content=clean_question)
    db.add(user_message)
    db.flush()

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )
    history.reverse()

    intent = classify_intent(clean_question, focus_document_id)
    source = SOURCE_GENERAL
    domain: str | None = None
    score: float | None = None
    citations: list[dict] = _source_citation(SOURCE_GENERAL)
    answer = ""

    doc_match = None
    if intent == IntentCategory.UPLOADED:
        doc_match = await asyncio.to_thread(
            search_uploaded_documents,
            db,
            user,
            clean_question,
            0.31,
            focus_document_id,
        )
        if doc_match:
            source = SOURCE_UPLOADS
            score = doc_match["score"]
            answer = await _synthesize_answer(clean_question, doc_match["chunk"], doc_match["file_name"], history)
            citations = _source_citation(
                SOURCE_UPLOADS,
                file_name=doc_match["file_name"],
                page_number=doc_match.get("page_number"),
                score=score,
            )
        elif focus_document_id:
            source = SOURCE_UPLOADS
            answer = "I could not find enough relevant information in the focused document to answer that confidently."
            citations = _source_citation(SOURCE_UPLOADS)
        else:
            intent = IntentCategory.GENERAL_AI

    # Fallback checking: check local knowledge base if not uploaded or uploaded returned nothing
    kb_match = None
    if intent in {IntentCategory.ONGC_KB, IntentCategory.ENTERPRISE_KB}:
        kb_match = await asyncio.to_thread(search_knowledge, clean_question)
    elif intent in {IntentCategory.GENERAL_AI, IntentCategory.GENERAL_KNOWLEDGE}:
        # Fallback check semantic similarity
        kb_match = await asyncio.to_thread(search_knowledge, clean_question, 0.30)
        if kb_match:
            # Map back to correct KB category
            if kb_match.domain in {"Human Resources", "Finance & Accounts", "Procurement", "IT & Cybersecurity"}:
                intent = IntentCategory.ENTERPRISE_KB
            else:
                intent = IntentCategory.ONGC_KB

    if intent == IntentCategory.ONGC_KB and kb_match:
        source = SOURCE_ONGC
        domain = kb_match.domain
        score = kb_match.score
        answer = await _synthesize_answer(clean_question, kb_match.chunk, SOURCE_ONGC, history)
        citations = _source_citation(SOURCE_ONGC, file_name=kb_match.source_file, score=score)
    elif intent == IntentCategory.ENTERPRISE_KB and kb_match:
        source = SOURCE_ENTERPRISE
        domain = kb_match.domain
        score = kb_match.score
        answer = await _synthesize_answer(clean_question, kb_match.chunk, SOURCE_ENTERPRISE, history)
        citations = _source_citation(SOURCE_ENTERPRISE, file_name=kb_match.source_file, score=score)
    elif intent in {IntentCategory.GENERAL_AI, IntentCategory.GENERAL_KNOWLEDGE, IntentCategory.UPLOADED}:
        # Ensure we only fallback if we didn't answer via uploads
        if intent != IntentCategory.UPLOADED or (intent == IntentCategory.UPLOADED and not doc_match and not focus_document_id):
            source = SOURCE_GENERAL
            answer = await _general_ai_answer(clean_question, history)
            citations = _source_citation(SOURCE_GENERAL)

    if is_new_session or session.title == "New Chat":
        session.title = _generate_chat_title(clean_question)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        source=source,
        domain=domain,
        similarity_score=score,
        response_time_ms=elapsed_ms,
        citations=json.dumps(citations, ensure_ascii=False),
    )
    session.updated_at = datetime.datetime.utcnow()
    db.add(assistant_message)
    db.add(
        AuditLog(
            user_id=user.id,
            question=clean_question,
            response=answer,
            domain=domain or "General",
            source=source,
            similarity_score=score,
            response_time_ms=elapsed_ms,
        )
    )

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    # Cache response
    _RESPONSE_CACHE[cache_key] = {
        "title": session.title,
        "answer": answer,
        "source": source,
        "domain": domain,
        "score": score,
        "citations": citations,
    }

    return {
        "session_id": session.id,
        "user_message_id": user_message.id,
        "assistant_message_id": assistant_message.id,
        "answer": answer,
        "source": source,
        "domain": domain,
        "response_time_ms": elapsed_ms,
        "citations": citations,
    }


async def stream_answer_question(
    db: Session,
    user: User,
    question: str,
    session_id: int | None,
    mode: str = "auto",
    focus_document_id: int | None = None,
) -> AsyncIterator[str]:
    started = time.perf_counter()
    clean_question = _clean_question(question)
    cache_key = (user.id, clean_question, focus_document_id, mode)

    session = db.get(ChatSession, session_id) if session_id else None
    is_new_session = False
    if not session or session.user_id != user.id:
        session = ChatSession(user_id=user.id, title="New Chat")
        db.add(session)
        db.flush()
        is_new_session = True

    session.active_document_id = None
    session.active_source = None
    if is_new_session or session.title == "New Chat":
        session.title = _generate_chat_title(clean_question)

    user_message = ChatMessage(session_id=session.id, role="user", content=clean_question)
    db.add(user_message)
    db.flush()

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content="",
        source=SOURCE_GENERAL,
        domain=None,
        similarity_score=None,
        response_time_ms=0,
        citations=json.dumps(_source_citation(SOURCE_GENERAL), ensure_ascii=False),
    )
    db.add(assistant_message)
    db.flush()

    yield _event(
        "meta",
        session_id=session.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        title=session.title,
    )

    if cache_key in _RESPONSE_CACHE:
        cached = _RESPONSE_CACHE[cache_key]
        yield _event("status", message="Using cached answer...")
        answer = cached["answer"]
        assistant_message.content = answer
        assistant_message.source = cached["source"]
        assistant_message.domain = cached["domain"]
        assistant_message.similarity_score = cached["score"]
        assistant_message.citations = json.dumps(cached["citations"], ensure_ascii=False)
        session.updated_at = datetime.datetime.utcnow()
        db.add(
            AuditLog(
                user_id=user.id,
                question=clean_question,
                response=answer,
                domain=cached["domain"] or "General",
                source=cached["source"],
                similarity_score=cached["score"],
                response_time_ms=0,
            )
        )
        db.commit()
        yield _event("token", text=answer)
        yield _event(
            "done",
            session_id=session.id,
            assistant_message_id=assistant_message.id,
            source=cached["source"],
            domain=cached["domain"],
            response_time_ms=0,
            citations=cached["citations"],
        )
        return

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(8)
        .all()
    )
    history.reverse()

    intent = classify_intent(clean_question, focus_document_id)
    source = SOURCE_GENERAL
    domain: str | None = None
    score: float | None = None
    citations: list[dict] = _source_citation(SOURCE_GENERAL)
    prompt = _build_general_prompt(clean_question, history)

    yield _event("status", message="Thinking...")

    doc_match = None
    if intent == IntentCategory.UPLOADED:
        yield _event("status", message="Searching uploaded documents...")
        doc_match = await asyncio.to_thread(
            search_uploaded_documents,
            db,
            user,
            clean_question,
            0.31,
            focus_document_id,
        )
        if doc_match:
            source = SOURCE_UPLOADS
            score = doc_match["score"]
            citations = _source_citation(
                SOURCE_UPLOADS,
                file_name=doc_match["file_name"],
                page_number=doc_match.get("page_number"),
                score=score,
            )
            prompt = _build_synthesis_prompt(clean_question, doc_match["chunk"], doc_match["file_name"], history)
        elif focus_document_id:
            answer = "I could not find enough relevant information in the focused document to answer that confidently."
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            assistant_message.content = answer
            assistant_message.source = SOURCE_UPLOADS
            assistant_message.response_time_ms = elapsed_ms
            assistant_message.citations = json.dumps(_source_citation(SOURCE_UPLOADS), ensure_ascii=False)
            session.updated_at = datetime.datetime.utcnow()
            db.commit()
            yield _event("token", text=answer)
            yield _event("done", session_id=session.id, assistant_message_id=assistant_message.id, source=SOURCE_UPLOADS, domain=None, response_time_ms=elapsed_ms, citations=_source_citation(SOURCE_UPLOADS))
            return
        else:
            intent = IntentCategory.GENERAL_AI

    kb_match = None
    if intent in {IntentCategory.ONGC_KB, IntentCategory.ENTERPRISE_KB}:
        yield _event("status", message="Searching knowledge base...")
        kb_match = await asyncio.to_thread(search_knowledge, clean_question)
    elif intent in {IntentCategory.GENERAL_AI, IntentCategory.GENERAL_KNOWLEDGE}:
        # Avoid semantic KB fallback for obvious general knowledge questions.
        if intent == IntentCategory.GENERAL_AI:
            kb_match = await asyncio.to_thread(search_knowledge, clean_question, 0.34)
            if kb_match:
                intent = IntentCategory.ENTERPRISE_KB if kb_match.domain in {"Human Resources", "Finance & Accounts", "Procurement", "IT & Cybersecurity"} else IntentCategory.ONGC_KB

    if intent == IntentCategory.ONGC_KB and kb_match:
        source = SOURCE_ONGC
        domain = kb_match.domain
        score = kb_match.score
        citations = _source_citation(SOURCE_ONGC, file_name=kb_match.source_file, score=score)
        prompt = _build_synthesis_prompt(clean_question, kb_match.chunk, SOURCE_ONGC, history)
    elif intent == IntentCategory.ENTERPRISE_KB and kb_match:
        source = SOURCE_ENTERPRISE
        domain = kb_match.domain
        score = kb_match.score
        citations = _source_citation(SOURCE_ENTERPRISE, file_name=kb_match.source_file, score=score)
        prompt = _build_synthesis_prompt(clean_question, kb_match.chunk, SOURCE_ENTERPRISE, history)

    yield _event("status", message="Generating response...")

    parts: list[str] = []
    async for token in _stream_ollama(prompt):
        parts.append(token)
        yield _event("token", text=token)

    answer = "".join(parts).strip() or "I could not generate a response right now."
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    assistant_message.content = answer
    assistant_message.source = source
    assistant_message.domain = domain
    assistant_message.similarity_score = score
    assistant_message.response_time_ms = elapsed_ms
    assistant_message.citations = json.dumps(citations, ensure_ascii=False)
    session.updated_at = datetime.datetime.utcnow()
    db.add(
        AuditLog(
            user_id=user.id,
            question=clean_question,
            response=answer,
            domain=domain or "General",
            source=source,
            similarity_score=score,
            response_time_ms=elapsed_ms,
        )
    )
    db.commit()

    _RESPONSE_CACHE[cache_key] = {
        "title": session.title,
        "answer": answer,
        "source": source,
        "domain": domain,
        "score": score,
        "citations": citations,
    }

    yield _event(
        "done",
        session_id=session.id,
        assistant_message_id=assistant_message.id,
        source=source,
        domain=domain,
        response_time_ms=elapsed_ms,
        citations=citations,
    )
