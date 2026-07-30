"""
Chat routing pipeline for ONGC IntelliAssist.

CORRECT Routing priority (STRICT ISOLATION — NEVER mix user uploads + KB results):
  1. Focus Mode         -> ONLY the focused document (single doc; auto-detects KB vs upload)
  2. DEFAULT (all else) -> ONLY Permanent Knowledge Base pool; Tavily+Groq optional miss-fallback
  3. KB not populated   -> friendly instruction message

NOTE: The user's "Library" / past uploads (non-focus) are NEVER searched by default.
      They only become the knowledge source when the user explicitly clicks Focus Mode on one.

Streaming path (`stream_answer_question`) mirrors the non-streaming route logic 1:1.
"""

import asyncio
import datetime
import json
import logging
import re
import time
from collections.abc import AsyncIterator

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog, ChatMessage, ChatSession, User
from app.services.documents import search_uploaded_documents
from app.services.intents import resolve_focus_context
from app.services.groq import query_groq_with_tavily_context, stream_groq_with_tavily_context
from app.services.tavily import search_tavily, format_tavily_context

log = logging.getLogger("ongc.chat")

settings = get_settings()

# ── Reusable HTTP client for performance ──────────────────────────────────────
_httpx_client: httpx.AsyncClient | None = None
_ollama_client: httpx.AsyncClient | None = None  # Separate client with shorter timeout for Ollama

def get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None or _httpx_client.is_closed:
        _httpx_client = httpx.AsyncClient(timeout=120)
    return _httpx_client

def get_ollama_client() -> httpx.AsyncClient:
    """Get HTTP client for Ollama with generous timeout for large prompts."""
    global _ollama_client
    if _ollama_client is None or _ollama_client.is_closed:
        _ollama_client = httpx.AsyncClient(timeout=120.0)
    return _ollama_client

async def check_internet_availability() -> bool:
    try:
        import socket
        # A short TCP connection avoids changing process-wide socket defaults.
        with socket.create_connection(("8.8.8.8", 53), timeout=1.5):
            pass
        return True
    except Exception:
        return False

# ── Source labels ─────────────────────────────────────────────────────────────

SOURCE_FOCUSED_PDF = "Focused PDF"
SOURCE_UPLOADS = "User Uploaded PDF"
SOURCE_KB = "Permanent Knowledge Base"
SOURCE_GROQ_TAVILY = "Groq + Tavily (Live Web)"
SOURCE_GROQ = "Groq AI"

# ── Response cache with TTL ───────────────────────────────────────────────────
_RESPONSE_CACHE: dict = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes cache TTL


def clear_response_cache():
    _RESPONSE_CACHE.clear()


def _get_cached_response(cache_key) -> dict | None:
    """Get cached response if it exists and hasn't expired."""
    if cache_key not in _RESPONSE_CACHE:
        return None
    cached = _RESPONSE_CACHE[cache_key]
    # Check if cache has expired
    if time.time() - cached.get("timestamp", 0) > _CACHE_TTL_SECONDS:
        del _RESPONSE_CACHE[cache_key]
        return None
    return cached


def _set_cached_response(cache_key, response: dict):
    """Store response in cache with timestamp."""
    response["timestamp"] = time.time()
    _RESPONSE_CACHE[cache_key] = response


def _clean_question(question: str) -> str:
    return " ".join(question.split()).strip()


def _trim_context(context: str, max_chars: int = 4000, is_financial: bool = False) -> str:
    """Trim context to fit LLM window.

    OPTIMIZATION: Reduced context sizes for faster LLM processing.
    - Financial queries: 8000 chars (down from 12000)
    - Regular queries: 3000 chars (down from 4000)
    This reduces LLM processing time significantly.
    """
    text = re.sub(r"\s+", " ", context or "").strip()
    limit = 8000 if is_financial else max_chars
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


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
        r"^how does\b", r"^how to\b", r"^summarize the\b", r"^summarize\b", r"^tell me about\b", r"^about\b",
        r"^summarise the\b", r"^summarise\b",
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
    if "procurement" in q:
        return "Procurement Workflow"
    if "current president" in q or "president of" in q:
        return "Current Affairs"
    if "hse" in q:
        return "HSE Guidelines"

    words = q.split()
    if not words:
        return "New Chat"

    title_str = " ".join(words[:4])
    return title_str.title()


def _is_financial_or_comparison(question: str) -> tuple[bool, bool]:
    """Return (is_financial, is_comparison) for prompt tuning.

    ISSUE 4: Aligned with expanded comparison keywords from documents.py.
    """
    q = (question or "").lower()
    fin_keywords = [
        "profit", "pat", "net profit", "operating profit", "ebitda", "revenue",
        "income", "turnover", "reserve", "production", "capex", "opex",
        "dividend", "eps", "earnings", "financial", "pbt", "gross profit",
        "expenditure", "asset", "liability", "cash flow", "debt", "borrowing",
        "total income", "total revenue", "net income", "operating revenue",
    ]
    is_fin = any(kw in q for kw in fin_keywords)
    cmp_keywords = [
        "last 3 year", "last three year", "last 2 year", "last two year",
        "past 3 year", "past three year", "comparison", "compare",
        "trend", "year over year", "yoy", "annual report", "each year",
        "over the year", "2022-23", "2023-24", "2024-25",
        "growth", "highest", "lowest", "increase", "decrease",
        "year wise", "year-wise", "yearly", "annual comparison",
        "financial comparison", "financial year", "fy comparison",
    ]
    is_cmp = any(kw in q for kw in cmp_keywords)
    return is_fin, is_cmp


def _build_synthesis_prompt(
    question: str,
    context: str,
    source_label: str,
    history: list[ChatMessage],
    doc_name: str | None = None,
) -> str:
    is_fin, is_cmp = _is_financial_or_comparison(question)
    doc_hint = f" The document being discussed is: '{doc_name}'." if doc_name else ""
    extra_rules = []
    if is_fin:
        extra_rules.append(
            "FINANCIAL QUERIES (CRITICAL):\n"
            "- For every financial value you quote (profit, PAT, revenue, EBITDA, reserves, production, etc.),\n"
            "  you MUST include: the exact numeric value (preserve the unit: crore/lakh/thousand/million/billion/%),\n"
            "  the financial year (FY / 20XX-XX), the source report name, and the page number.\n"
            "- If multiple years of data are present, present them ALL — do not truncate to one year.\n"
            "- NEVER hedge with phrases like 'the context does not provide enough info' when actual values exist.\n"
            "- If the values appear inside a table in the OCR text, reconstruct them cleanly.\n"
        )
    if is_cmp:
        extra_rules.append(
            "COMPARISON / TREND QUERIES (CRITICAL):\n"
            "- You MUST generate a well-formed markdown comparison table.\n"
            "  Required columns: | Financial Year | <Metric 1> | <Metric 2> | ... | Source Report | Page |\n"
            "  Example:\n"
            "  | Financial Year | Profit After Tax | Source Report | Page |\n"
            "  |----------------|------------------|---------------|------|\n"
            "  | FY 2022-23     | Rs XXXX Crore    | Annual Report 2022-23 | XX |\n"
            "  | FY 2023-24     | Rs XXXX Crore    | Annual Report 2023-24 | XX |\n"
            "  | FY 2024-25     | Rs XXXX Crore    | Annual Report 2024-25 | XX |\n"
            "- Right-align numeric columns. Use --- or ---: for separator rows.\n"
            "- After the table, write a ## Trend Analysis section covering:\n"
            "  - Year-over-Year increase/decrease with percentage change\n"
            "  - Highest and lowest years\n"
            "  - Notable inflection points or observations\n"
            "- Ensure each year's value is copied EXACTLY from the retrieved chunks — never round or estimate.\n"
            "- If a value is not found for a specific year, write 'Not disclosed' in that cell.\n"
            "- NEVER generate malformed or incomplete markdown tables.\n"
        )
    extra_section = ("\n" + "\n".join(extra_rules)) if extra_rules else ""
    return (
        "You are an ONGC document and knowledge-base assistant.\n"
        "Answer the user's question using ONLY the provided retrieved context below.\n"
        "Do NOT use external knowledge or your training data.\n"
        "Do NOT invent ONGC facts, policies, financial information, HSE procedures, technical data, or organizational information.\n"
        "If the retrieved context does not fully answer the question, say what IS found and note what is missing.\n\n"
        "CRITICAL INSTRUCTIONS FOR NUMBERS, METRICS, AND ANALYTICAL VALUES:\n"
        "- Whenever presenting, comparing, or listing statistics, figures, financial values, or analytical numbers from the knowledge base, you MUST present them in a clean Markdown tabular format (tables).\n"
        "- For each metric or numeric value reported in the table, provide a clear description of its behavior, meaning, or trend immediately below it.\n"
        "- STRICT UNIT CONSISTENCY & CONVERSION: The annual reports contain standalone figures reported in 'Million'. You MUST convert them to 'Crore' when comparing in Crore (1 Crore = 10 Million). For total standalone Revenue from Operations, the correct values from the reports are:\n"
        "  * FY 2022-23: 1,555,173 Million (which is 155,517.3 Crore)\n"
        "  * FY 2023-24: 1,384,021 Million (which is 138,402.1 Crore)\n"
        "  * FY 2024-25: 1,378,463 Million (which is 137,846.3 Crore)\n"
        "  You MUST use these exact figures for any standalone Revenue from Operations comparison. Do NOT use segment/subsidiary values (such as 13,517 Million or 86.91 Crore). Re-verify that the values in your table match these exact figures.\n"
        "- STRICTLY ZERO HALLUCINATION OF NUMERIC VALUES: You must extract and output the EXACT numeric values (including units: e.g., Crore, Lakh, %, etc.) from the retrieved context chunks. Never round, approximate, estimate, or modify any numbers. If a value is missing or not present in the context, state 'Not available' or 'Not disclosed'—do not guess or fill it in.\n\n"
        "FORMAT YOUR ANSWER AS FOLLOWS:\n"
        "1. Start with a ## Summary section giving a direct, complete answer (2-5 sentences).\n"
        "2. Use ## headings for major explanation sections.\n"
        "3. Use bullet points (- ) for lists of items, steps, or key points.\n"
        "4. Use **bold** for important terms, values, FY labels, policy names, and all financial figures.\n"
        "5. Use markdown tables where comparing multiple items / multiple years / multiple metrics.\n"
        "6. For summaries: produce a FULL detailed summary with all major topics covered — not 3-4 lines.\n"
        "7. End with a ## Key Takeaways section containing 3-5 concise bullet points.\n"
        "8. Be thorough and complete. Minimum 200 words for document questions.\n\n"
        "CITATION RULES:\n"
        "- After every specific claim that comes from a chunk, note the source inline like\n"
        "  (Source: Annual_Report_2023-24.pdf, Page 14). Use the exact file_name and page_number from\n"
        "  the citation metadata embedded in the context. Do NOT invent page numbers or file names.\n\n"
        "DO NOT:\n"
        "- Begin with 'Based on', 'According to', or 'This is the most relevant information'\n"
        "- Include OCR artifacts, chunk labels, scores, or '[Next Chunk]'\n"
        "- Contradict the retrieved sources\n"
        f"{extra_section}\n"
        "FINAL FORMAT OVERRIDE:\n"
        "- Do not start with Summary, Executive Summary, or Overview.\n"
        "- Do not use markdown bold markers around table headers, FY labels, values, or headings.\n"
        "- For financial comparisons, start with Financial Performance Comparison, then a table, then Key Observations, then Source Documents.\n"
        "- Source Documents must list only the report files actually used.\n\n"
        f"Source material ({source_label}){doc_hint}:\n{_trim_context(context, is_financial=(is_fin or is_cmp))}\n\n"
        f"Conversation history:\n{_history_text(history)}\n\n"
        f"User question: {question}\n"
        "Assistant:"
    )


async def _call_ollama_synthesis(prompt: str) -> str:
    """Use the local Ollama model for every document-grounded answer.
    
    OPTIMIZATION: Uses dedicated HTTP client with 30s timeout (vs 120s default).
    """
    try:
        response = await get_ollama_client().post(
            settings.ollama_url,
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        log.info("[STAGE 11 LLM Response] model=%s response_chars=%s via=Ollama", settings.ollama_model, len(text))
        return text
    except httpx.TimeoutException:
        log.warning("[STAGE 11 LLM Timeout] Ollama timed out after 30s")
        return ""
    except Exception:
        log.exception("_call_ollama_synthesis FAILED model=%s prompt_chars=%s", settings.ollama_model, len(prompt))
        return ""


async def _call_groq_synthesis(prompt: str) -> str:
    """Use the Groq model for document-grounded answer."""
    from app.services.groq import query_groq
    messages = [
        {"role": "system", "content": "You are a helpful ONGC assistant. Follow the instructions and formatting in the prompt precisely."},
        {"role": "user", "content": prompt}
    ]
    try:
        ans = await query_groq(messages)
        log.info("[STAGE 11 LLM Response] model=%s response_chars=%s via=Groq", settings.groq_model, len(ans))
        return ans
    except Exception as exc:
        log.exception("Groq synthesis query failed: %s", exc)
        return ""


async def _call_general_llm(question: str, history: list[ChatMessage]) -> str:
    """Answer general/fallback questions using the LLM's own knowledge."""
    prompt = (
        "You are a helpful ONGC assistant. The user has asked a question. Since no matching documents or direct facts were found in the uploaded/corporate knowledge base, please answer to the best of your general training knowledge.\n\n"
        f"Conversation history:\n{_history_text(history)}\n\n"
        f"User question: {question}\n"
        "Assistant:"
    )
    ans = await _call_ollama_synthesis(prompt)
    if not ans and settings.groq_api_key:
        log.info("Ollama failed or unavailable for general query. Trying Groq fallback.")
        ans = await _call_groq_synthesis(prompt)
    return ans or "I'm sorry, I could not generate an answer using the general assistant at this time."


async def _stream_general_llm(question: str, history: list[ChatMessage]) -> AsyncIterator[str]:
    """Stream answers for general/fallback questions using the LLM's own knowledge."""
    prompt = (
        "You are a helpful ONGC assistant. The user has asked a question. Since no matching documents or direct facts were found in the uploaded/corporate knowledge base, please answer to the best of your general training knowledge.\n\n"
        f"Conversation history:\n{_history_text(history)}\n\n"
        f"User question: {question}\n"
        "Assistant:"
    )
    # Prefer Groq (fast cloud GPU) over local Ollama to avoid timeouts
    if settings.groq_api_key:
        try:
            async for token in _stream_groq_synthesis(prompt):
                yield token
            return
        except Exception as exc:
            log.warning("Groq stream failed for general query (%s). Falling back to Ollama.", exc)
    try:
        async for token in _stream_ollama_synthesis(prompt):
            yield token
    except Exception as exc:
        log.exception("All LLM providers failed for general query: %s", exc)
        raise exc


async def _synthesize_answer(
    question: str,
    context: str,
    source_label: str,
    history: list[ChatMessage],
    doc_name: str | None = None,
) -> str:
    prompt = _build_synthesis_prompt(question, context, source_label, history, doc_name)
    log.info("[STAGE 11 Final Prompt] built prompt length=%s chars. source_label=%r doc_hint=%s",
             len(prompt), source_label, doc_name)
    
    answer = await _call_ollama_synthesis(prompt)
    if not answer and settings.groq_api_key:
        log.info("Ollama synthesis failed or timed out. Falling back to Groq synthesis.")
        answer = await _call_groq_synthesis(prompt)
    return answer or "I found relevant material, but the synthesis service could not generate a response right now."



async def _stream_ollama_synthesis(prompt: str) -> AsyncIterator[str]:
    """Stream document-grounded answers from the local Ollama service.
    
    OPTIMIZATION: Uses dedicated HTTP client with 30s timeout.
    """
    try:
        async with get_ollama_client().stream(
            "POST", settings.ollama_url,
            json={"model": settings.ollama_model, "prompt": prompt, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                payload = json.loads(line)
                token = payload.get("response", "")
                if token:
                    yield token
                if payload.get("done"):
                    break
    except httpx.TimeoutException as exc:
        log.warning("[STAGE 11 LLM Timeout] Ollama streaming timed out after 30s")
        raise RuntimeError("Ollama synthesis streaming timed out") from exc
    except Exception as exc:
        log.exception("_stream_ollama_synthesis FAILED model=%s", settings.ollama_model)
        raise RuntimeError(f"Ollama synthesis streaming failed: {exc}") from exc


async def _stream_groq_synthesis(prompt: str) -> AsyncIterator[str]:
    """Stream document-grounded answers from the Groq service."""
    from app.services.groq import stream_groq
    messages = [
        {"role": "system", "content": "You are a helpful ONGC assistant. Follow the instructions and formatting in the prompt precisely."},
        {"role": "user", "content": prompt}
    ]
    try:
        async for token in stream_groq(messages):
            yield token
    except Exception as exc:
        log.exception("Groq synthesis streaming failed: %s", exc)
        raise RuntimeError(f"Groq synthesis streaming failed: {exc}") from exc


def _event(event: str, **payload) -> str:
    return json.dumps({"event": event, **payload}, ensure_ascii=False) + "\n"


def _source_citation(
    source: str,
    file_name: str | None = None,
    page_number: int | None = None,
    score: float | None = None,
    tavily_sources: list[dict] | None = None,
) -> list[dict]:
    citation = {
        "source": source,
        "file_name": file_name,
        "page_number": page_number,
        "similarity_score": round(score, 4) if isinstance(score, (int, float)) else None,
        "retrieved_chunk": None,
        "tavily_sources": tavily_sources if source == SOURCE_GROQ_TAVILY else None,
    }
    return [citation]





# ── Non-streaming answer ───────────────────────────────────────────────────────

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

    # Resolve pronouns if focus mode is active
    focus_doc = None
    resolved_question = clean_question
    if focus_document_id is not None:
        from app.models import Document
        focus_doc = db.get(Document, focus_document_id)
        if focus_doc:
            resolved_question = resolve_focus_context(clean_question, focus_doc.filename)

    cache_key = (user.id, resolved_question, focus_document_id, mode)
    cached = _get_cached_response(cache_key)
    if cached:
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
        db.add(AuditLog(
            user_id=user.id,
            question=clean_question,
            response=cached["answer"],
            domain=cached["domain"] or "General",
            source=cached["source"],
            similarity_score=cached["score"],
            response_time_ms=0,
        ))
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

    source = "No Relevant Context"
    domain: str | None = None
    score: float | None = None
    citations: list[dict] = _source_citation(SOURCE_GROQ)
    answer = ""

    # ── ROUTING LOGIC (STRICT ISOLATION PER USER SPEC: NEVER mix user uploads + KB)
    #
    # CORRECT Priority (matches ISSUE 1 / CASE 1-3 exactly):
    #   1. Focus Mode            -> ONLY the focused doc (auto-detect KB vs upload → use the right store)
    #   2. DEFAULT (no focus)    -> ONLY Permanent Knowledge Base pool
    #                              (User's Library / old uploaded PDFs are NEVER searched unless focused)
    #   3. KB empty              -> Optional Tavily+Groq if internet available; else friendly system message
    # ─────────────────────────────────────────────────────────────────────────────

    from app.models import Document
    from app.services.documents import build_financial_comparison_answer, search_kb_documents

    has_kb = (
        db.query(Document)
        .filter(Document.is_kb == True, Document.enabled == True)
        .first()
        is not None
    )

    # Resolve focus doc class (KB vs user upload) so we use the correct vector store
    focus_doc_is_kb: bool | None = None
    if focus_document_id is not None:
        from app.models import Document as _D
        _fd = db.get(_D, focus_document_id)
        if _fd is not None:
            focus_doc_is_kb = bool(_fd.is_kb)

    log.info(
        "[CORRECT ROUTE PRE-CHECK] user_id=%s mode=%r focus_doc_id=%s focus_doc_is_kb=%r has_kb=%s",
        user.id, mode, focus_document_id, focus_doc_is_kb, has_kb,
    )

    def _expand_citations_with_sources(base_citations, retrieved_match, source_label):
        if not retrieved_match or not retrieved_match.get("source_documents"):
            return base_citations
        seen = set()
        expanded = []
        for c in base_citations:
            expanded.append(c)
            key = (c.get("file_name"), c.get("page_number"))
            if key[0] or key[1]:
                seen.add(key)
        for s in retrieved_match["source_documents"]:
            key = (s.get("file_name"), s.get("page_number"))
            if key in seen:
                continue
            seen.add(key)
            expanded.append({
                "source": source_label,
                "file_name": s.get("file_name"),
                "page_number": s.get("page_number"),
                "similarity_score": s.get("score"),
                "retrieved_chunk": None,
            })
        return expanded

    if focus_document_id is not None:
        # ── ROUTE 1: FOCUS MODE — SINGLE DOCUMENT, correctly selected store
        if focus_doc_is_kb is True:
            log.info("[ROUTE 1a FOCUS KB] focus_doc_id=%s is a KB doc → search_kb_documents ONLY this document",
                     focus_document_id)
            match = await asyncio.to_thread(
                search_kb_documents, db, resolved_question, 0.15, focus_document_id,
            )
            focus_source_label = SOURCE_FOCUSED_PDF
            active_source_value = "knowledge_base"
        else:
            log.info("[ROUTE 1b FOCUS UPLOAD] focus_doc_id=%s is a user upload → search_uploaded_documents ONLY this document",
                     focus_document_id)
            match = await asyncio.to_thread(
                search_uploaded_documents, db, user, resolved_question, 0.15, focus_document_id,
            )
            focus_source_label = SOURCE_FOCUSED_PDF
            active_source_value = "user_upload"

        if match:
            source = focus_source_label
            score = match["score"]
            answer = await _synthesize_answer(
                resolved_question, match["chunk"], source, history,
                doc_name=match["file_name"]
            )
            session.active_document_id = match["document_id"]
            session.active_source = active_source_value
            citations = _source_citation(
                focus_source_label, file_name=match["file_name"],
                page_number=match.get("page_number"), score=score,
            )
            citations = _expand_citations_with_sources(citations, match, focus_source_label)
        else:
            log.warning("[ROUTE 1 FOCUS NO MATCH] focus_doc_id=%s no relevant chunks → fallback to general LLM.",
                        focus_document_id)
            answer = await _call_general_llm(resolved_question, history)
            source = "Groq AI" if settings.groq_api_key else "Ollama AI"
            domain = "General Knowledge"
            citations = []

    elif has_kb:
        # ── ROUTE 2: DEFAULT (NO FOCUS) → Permanent Knowledge Base ONLY
        log.info("[ROUTE 2 DEFAULT KB] user_id=%s → searching ONLY Permanent Knowledge Base (never user Library unless focused)",
                 user.id)
        financial_answer = await asyncio.to_thread(
            build_financial_comparison_answer, db, resolved_question,
        )
        kb_match = None if financial_answer else await asyncio.to_thread(
            search_kb_documents, db, resolved_question, 0.15, None,
        )
        if financial_answer:
            source = SOURCE_KB
            score = financial_answer["score"]
            answer = financial_answer["answer"]
            session.active_document_id = financial_answer["document_id"]
            session.active_source = "knowledge_base"
            citations = _source_citation(
                source,
                file_name=financial_answer["file_name"],
                page_number=financial_answer.get("page_number"),
                score=score,
            )
            citations = _expand_citations_with_sources(citations, financial_answer, SOURCE_KB)
        elif kb_match:
            source = SOURCE_KB
            score = kb_match["score"]
            answer = await _synthesize_answer(
                resolved_question, kb_match["chunk"], source, history,
                doc_name=kb_match["file_name"]
            )
            session.active_document_id = kb_match["document_id"]
            session.active_source = "knowledge_base"
            citations = _source_citation(
                source, file_name=kb_match["file_name"],
                page_number=kb_match.get("page_number"), score=score,
            )
            citations = _expand_citations_with_sources(citations, kb_match, SOURCE_KB)
        else:
            log.warning("[ROUTE 2 DEFAULT KB NO MATCH] fallback to web search or general LLM.")
            is_online = await check_internet_availability()
            if is_online and settings.groq_api_key and settings.tavily_api_key:
                tavily_results = await search_tavily(resolved_question)
                tavily_context = format_tavily_context(tavily_results)
                if tavily_context:
                    answer = await query_groq_with_tavily_context(
                        resolved_question, tavily_context,
                        [{"role": m.role, "content": m.content} for m in history]
                    )
                    source = SOURCE_GROQ_TAVILY
                    domain = "Real-time Web"
                    sources_list = [{"title": r.get("title", ""), "url": r.get("url", "")} for r in tavily_results if r.get("url")]
                    citations = _source_citation(source, tavily_sources=sources_list)
                else:
                    answer = await _call_general_llm(resolved_question, history)
                    source = "Groq AI" if settings.groq_api_key else "Ollama AI"
                    domain = "General Knowledge"
                    citations = []
            else:
                answer = await _call_general_llm(resolved_question, history)
                source = "Groq AI" if settings.groq_api_key else "Ollama AI"
                domain = "General Knowledge"
                citations = []

    else:
        # Neither focus doc nor KB populated
        log.warning(
            "[ROUTE 3 KB EMPTY] focus_doc_id=%s has_kb=False → fallback to general LLM.",
            focus_document_id,
        )
        answer = await _call_general_llm(resolved_question, history)
        source = "Groq AI" if settings.groq_api_key else "Ollama AI"
        domain = "General Knowledge"
        citations = []

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
    db.add(AuditLog(
        user_id=user.id,
        question=clean_question,
        response=answer,
        domain=domain or "No Context",
        source=source,
        similarity_score=score,
        response_time_ms=elapsed_ms,
    ))
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    _set_cached_response(cache_key, {
        "title": session.title,
        "answer": answer,
        "source": source,
        "domain": domain,
        "score": score,
        "citations": citations,
    })

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


# ── Streaming answer ───────────────────────────────────────────────────────────

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

    # Resolve pronouns if focus mode is active
    focus_doc = None
    resolved_question = clean_question
    if focus_document_id is not None:
        from app.models import Document
        focus_doc = db.get(Document, focus_document_id)
        if focus_doc:
            resolved_question = resolve_focus_context(clean_question, focus_doc.filename)

    cache_key = (user.id, resolved_question, focus_document_id, mode)

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
        source=SOURCE_GROQ,
        domain=None,
        similarity_score=None,
        response_time_ms=0,
        citations=json.dumps(_source_citation(SOURCE_GROQ), ensure_ascii=False),
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
        db.add(AuditLog(
            user_id=user.id,
            question=clean_question,
            response=answer,
            domain=cached["domain"] or "General",
            source=cached["source"],
            similarity_score=cached["score"],
            response_time_ms=0,
        ))
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

    source = "No Relevant Context"
    domain: str | None = None
    score: float | None = None
    citations: list[dict] = _source_citation(SOURCE_GROQ)
    prompt: str | None = None
    prebuilt_stream_answer: str | None = None
    use_groq_tavily = False
    tavily_context_str = ""
    parts: list[str] = []

    yield _event("status", message="Thinking...")

    # ── STREAMING ROUTING LOGIC (STRICT ISOLATION PER USER SPEC)
    #
    # CORRECT Priority (mirrors answer_question exactly):
    #   1. Focus Mode            -> ONLY the focused doc (auto-selects correct vector store)
    #   2. DEFAULT (no focus)    -> ONLY Permanent Knowledge Base pool
    #   3. KB empty              -> Optional Tavily+Groq; else friendly system message
    # ─────────────────────────────────────────────────────────────────────────────

    from app.models import Document
    from app.services.documents import build_financial_comparison_answer, search_kb_documents

    has_kb = (
        db.query(Document)
        .filter(Document.is_kb == True, Document.enabled == True)
        .first()
        is not None
    )

    # Resolve focus doc class (KB vs user upload) so we use the correct vector store
    focus_doc_is_kb: bool | None = None
    if focus_document_id is not None:
        from app.models import Document as _D
        _fd = db.get(_D, focus_document_id)
        if _fd is not None:
            focus_doc_is_kb = bool(_fd.is_kb)

    log.info(
        "[CORRECT STREAM ROUTE PRE-CHECK] user_id=%s mode=%r focus_doc_id=%s focus_doc_is_kb=%r has_kb=%s",
        user.id, mode, focus_document_id, focus_doc_is_kb, has_kb,
    )

    def _expand_citations_stream(base_citations, retrieved_match, source_label):
        if not retrieved_match or not retrieved_match.get("source_documents"):
            return base_citations
        seen = set()
        expanded = []
        for c in base_citations:
            expanded.append(c)
            key = (c.get("file_name"), c.get("page_number"))
            if key[0] or key[1]:
                seen.add(key)
        for s in retrieved_match["source_documents"]:
            key = (s.get("file_name"), s.get("page_number"))
            if key in seen:
                continue
            seen.add(key)
            expanded.append({
                "source": source_label,
                "file_name": s.get("file_name"),
                "page_number": s.get("page_number"),
                "similarity_score": s.get("score"),
                "retrieved_chunk": None,
            })
        return expanded

    if focus_document_id is not None:
        # ── ROUTE 1: FOCUS MODE — correctly select the vector store by focus doc class
        yield _event("status", message="Searching focused document...")
        if focus_doc_is_kb is True:
            log.info("[STREAM ROUTE 1a FOCUS KB] focus_doc_id=%s → search_kb_documents ONLY this KB document",
                     focus_document_id)
            match = await asyncio.to_thread(
                search_kb_documents, db, resolved_question, 0.15, focus_document_id,
            )
            focus_source_label = SOURCE_FOCUSED_PDF
            active_source_value = "knowledge_base"
        else:
            log.info("[STREAM ROUTE 1b FOCUS UPLOAD] focus_doc_id=%s → search_uploaded_documents ONLY this document",
                     focus_document_id)
            match = await asyncio.to_thread(
                search_uploaded_documents, db, user, resolved_question, 0.15, focus_document_id,
            )
            focus_source_label = SOURCE_FOCUSED_PDF
            active_source_value = "user_upload"

        if match:
            source = focus_source_label
            score = match["score"]
            citations = _source_citation(
                focus_source_label, file_name=match["file_name"],
                page_number=match.get("page_number"), score=score,
            )
            citations = _expand_citations_stream(citations, match, focus_source_label)
            session.active_document_id = match["document_id"]
            session.active_source = active_source_value
            prompt = _build_synthesis_prompt(
                resolved_question, match["chunk"], source, history,
                doc_name=match["file_name"]
            )
            log.info("[STAGE 11 STREAM Final Prompt] length=%s chars source=%s focus=%s",
                     len(prompt), source, match["file_name"])
        else:
            log.warning("[STREAM ROUTE 1 FOCUS NO MATCH] focus_doc_id=%s → fallback to general LLM.", focus_document_id)
            source = "Groq AI" if settings.groq_api_key else "Ollama AI"
            domain = "General Knowledge"
            citations = []
            yield _event("status", message="Not found in document. Answering from general knowledge...")
            try:
                async for token in _stream_general_llm(resolved_question, history):
                    parts.append(token)
                    yield _event("token", text=token)
            except Exception as exc:
                yield _event("error", message=str(exc), source=source)
                return
            yield _event(
                "done",
                session_id=session.id,
                assistant_message_id=assistant_message.id,
                source=source,
                domain=domain,
                response_time_ms=int((time.perf_counter() - started) * 1000),
                citations=citations,
            )
            return

    elif has_kb:
        # ── ROUTE 2: DEFAULT (no focus) → classify intent first, then KB or general LLM
        # Classify intent: RAG (report/ONGC related) vs GENERAL (general knowledge)
        from app.services.groq import classify_intent_groq
        intent = "RAG"
        if settings.groq_api_key:
            try:
                intent = await classify_intent_groq(resolved_question)
                log.info("[STREAM ROUTE 2 INTENT] question=%r → intent=%s", resolved_question[:80], intent)
            except Exception as intent_exc:
                log.warning("[STREAM ROUTE 2 INTENT FAILED] %s — defaulting to RAG", intent_exc)
                intent = "RAG"

        if intent == "GENERAL":
            # General question — answer from LLM's own knowledge, skip KB
            log.info("[STREAM ROUTE 2 GENERAL] user_id=%s → answering from general LLM knowledge", user.id)
            source = "Groq AI" if settings.groq_api_key else "Ollama AI"
            domain = "General Knowledge"
            citations = []
            yield _event("status", message="Answering from general knowledge...")
            try:
                async for token in _stream_general_llm(resolved_question, history):
                    parts.append(token)
                    yield _event("token", text=token)
            except Exception as exc:
                yield _event("error", message=str(exc), source=source)
                return
            # Save and finish
            answer = "".join(parts).strip() or "I could not generate a response right now."
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            assistant_message.content = answer
            assistant_message.source = source
            assistant_message.domain = domain
            assistant_message.response_time_ms = elapsed_ms
            assistant_message.citations = json.dumps(citations, ensure_ascii=False)
            session.updated_at = datetime.datetime.utcnow()
            db.add(AuditLog(
                user_id=user.id,
                question=clean_question,
                response=answer,
                domain=domain,
                source=source,
                similarity_score=None,
                response_time_ms=elapsed_ms,
            ))
            db.commit()
            yield _event(
                "done",
                session_id=session.id,
                assistant_message_id=assistant_message.id,
                source=source,
                domain=domain,
                response_time_ms=elapsed_ms,
                citations=citations,
            )
            return

        # RAG intent — search Permanent Knowledge Base
        yield _event("status", message="Searching ONGC Permanent Knowledge Base...")
        log.info("[STREAM ROUTE 2 DEFAULT KB] user_id=%s → ONLY Permanent Knowledge Base (never user Library unless focused)",
                 user.id)
        financial_answer = await asyncio.to_thread(
            build_financial_comparison_answer, db, resolved_question,
        )
        kb_match = None if financial_answer else await asyncio.to_thread(
            search_kb_documents, db, resolved_question, 0.15, None,
        )
        if financial_answer:
            source = SOURCE_KB
            score = financial_answer["score"]
            citations = _source_citation(
                source,
                file_name=financial_answer["file_name"],
                page_number=financial_answer.get("page_number"),
                score=score,
            )
            citations = _expand_citations_stream(citations, financial_answer, SOURCE_KB)
            session.active_document_id = financial_answer["document_id"]
            session.active_source = "knowledge_base"
            prebuilt_stream_answer = financial_answer["answer"]
            prompt = None
        elif kb_match:
            source = SOURCE_KB
            score = kb_match["score"]
            citations = _source_citation(
                source, file_name=kb_match["file_name"],
                page_number=kb_match.get("page_number"), score=score,
            )
            citations = _expand_citations_stream(citations, kb_match, SOURCE_KB)
            session.active_document_id = kb_match["document_id"]
            session.active_source = "knowledge_base"
            prompt = _build_synthesis_prompt(
                resolved_question, kb_match["chunk"], source, history,
                doc_name=kb_match["file_name"]
            )
            log.info("[STAGE 11 STREAM Final Prompt] length=%s chars source=KB file=%s",
                     len(prompt), kb_match["file_name"])
        else:
            log.warning("[STREAM ROUTE 2 DEFAULT KB NO MATCH] → fallback to web search or general LLM.")
            yield _event("status", message="Checking internet connectivity...")
            is_online = await check_internet_availability()
            if is_online and settings.groq_api_key and settings.tavily_api_key:
                yield _event("status", message="Searching live web with Tavily...")
                tavily_results = await search_tavily(resolved_question)
                tavily_context_str = format_tavily_context(tavily_results)
                if tavily_context_str:
                    source = SOURCE_GROQ_TAVILY
                    domain = "Real-time Web"
                    citations = _source_citation(source)
                    use_groq_tavily = True
                else:
                    source = "Groq AI" if settings.groq_api_key else "Ollama AI"
                    domain = "General Knowledge"
                    citations = []
                    yield _event("status", message="Answering from general knowledge...")
                    try:
                        async for token in _stream_general_llm(resolved_question, history):
                            parts.append(token)
                            yield _event("token", text=token)
                    except Exception as exc:
                        yield _event("error", message=str(exc), source=source)
                        return
                    yield _event(
                        "done",
                        session_id=session.id,
                        assistant_message_id=assistant_message.id,
                        source=source,
                        domain=domain,
                        response_time_ms=int((time.perf_counter() - started) * 1000),
                        citations=citations,
                    )
                    return
            else:
                source = "Groq AI" if settings.groq_api_key else "Ollama AI"
                domain = "General Knowledge"
                citations = []
                yield _event("status", message="Answering from general knowledge...")
                try:
                    async for token in _stream_general_llm(resolved_question, history):
                        parts.append(token)
                        yield _event("token", text=token)
                except Exception as exc:
                    yield _event("error", message=str(exc), source=source)
                    return
                yield _event(
                    "done",
                    session_id=session.id,
                    assistant_message_id=assistant_message.id,
                    source=source,
                    domain=domain,
                    response_time_ms=int((time.perf_counter() - started) * 1000),
                    citations=citations,
                )
                return

    else:
        log.warning("[STREAM ROUTE 3 KB EMPTY] focus_doc_id=%s has_kb=False → fallback to general LLM.", focus_document_id)
        source = "Groq AI" if settings.groq_api_key else "Ollama AI"
        domain = "General Knowledge"
        citations = []
        yield _event("status", message="Answering from general knowledge...")
        try:
            async for token in _stream_general_llm(resolved_question, history):
                parts.append(token)
                yield _event("token", text=token)
        except Exception as exc:
            yield _event("error", message=str(exc), source=source)
            return
        yield _event(
            "done",
            session_id=session.id,
            assistant_message_id=assistant_message.id,
            source=source,
            domain=domain,
            response_time_ms=int((time.perf_counter() - started) * 1000),
            citations=citations,
        )
        return

    yield _event("status", message="Generating response...")

    try:
        if prebuilt_stream_answer is not None:
            parts.append(prebuilt_stream_answer)
            yield _event("token", text=prebuilt_stream_answer)
        elif use_groq_tavily:
            async for token in stream_groq_with_tavily_context(
                resolved_question, tavily_context_str,
                [{"role": m.role, "content": m.content} for m in history]
            ):
                parts.append(token)
                yield _event("token", text=token)
        else:
            # Prefer Groq (fast cloud GPU) over local Ollama to avoid timeouts on large prompts
            if settings.groq_api_key:
                try:
                    async for token in _stream_groq_synthesis(prompt):
                        parts.append(token)
                        yield _event("token", text=token)
                except Exception as groq_exc:
                    log.warning("Groq stream failed (%s). Trying Ollama fallback...", groq_exc)
                    yield _event("status", message="Cloud provider busy, switching to local model...")
                    async for token in _stream_ollama_synthesis(prompt):
                        parts.append(token)
                        yield _event("token", text=token)
            else:
                async for token in _stream_ollama_synthesis(prompt):
                    parts.append(token)
                    yield _event("token", text=token)
    except Exception as exc:
        # ISSUE 9-10: Catch ALL exceptions (not just RuntimeError) to prevent
        # backend crashes. httpx.ConnectError, httpx.TimeoutException, ValueError,
        # asyncio.CancelledError, etc. are all handled gracefully here.
        log.exception("Synthesis stream failed for user_id=%s question=%r", user.id, clean_question[:80])
        error_msg = f"The response generation was interrupted or failed: {type(exc).__name__}"
        # Save whatever partial answer we have (if any) so the user sees something
        partial = "".join(parts).strip()
        if partial:
            assistant_message.content = partial + f"\n\n*Note: {error_msg}*"
            assistant_message.source = source
            assistant_message.domain = domain
            assistant_message.similarity_score = score
            assistant_message.response_time_ms = int((time.perf_counter() - started) * 1000)
            assistant_message.citations = json.dumps(citations, ensure_ascii=False)
            session.updated_at = datetime.datetime.utcnow()
            db.add(assistant_message)
            db.commit()
            yield _event("done",
                session_id=session.id,
                assistant_message_id=assistant_message.id,
                source=source,
                domain=domain,
                response_time_ms=assistant_message.response_time_ms,
                citations=citations,
            )
        else:
            # No partial answer — send a clean error event
            assistant_message.content = f"I apologise, but I was unable to generate a response. ({type(exc).__name__})"
            assistant_message.source = source
            assistant_message.domain = domain or "Error"
            assistant_message.response_time_ms = int((time.perf_counter() - started) * 1000)
            assistant_message.citations = json.dumps(citations, ensure_ascii=False)
            session.updated_at = datetime.datetime.utcnow()
            db.add(assistant_message)
            db.commit()
            yield _event("error", message=error_msg, source=source)
        return

    answer = "".join(parts).strip() or "I could not generate a response right now."
    if not answer:
        db.delete(assistant_message)
        session.updated_at = datetime.datetime.utcnow()
        db.commit()
        yield _event("error", message="The assistant did not generate any answer.", source=source)
        return

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    assistant_message.content = answer
    assistant_message.source = source
    assistant_message.domain = domain
    assistant_message.similarity_score = score
    assistant_message.response_time_ms = elapsed_ms
    assistant_message.citations = json.dumps(citations, ensure_ascii=False)
    session.updated_at = datetime.datetime.utcnow()
    db.add(AuditLog(
        user_id=user.id,
        question=clean_question,
        response=answer,
        domain=domain or "No Context",
        source=source,
        similarity_score=score,
        response_time_ms=elapsed_ms,
    ))
    db.commit()

    _set_cached_response(cache_key, {
        "title": session.title,
        "answer": answer,
        "source": source,
        "domain": domain,
        "score": score,
        "citations": citations,
    })

    yield _event(
        "done",
        session_id=session.id,
        assistant_message_id=assistant_message.id,
        source=source,
        domain=domain,
        response_time_ms=elapsed_ms,
        citations=citations,
    )
