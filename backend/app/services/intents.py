"""
Intent classification for ONGC IntelliAssist routing pipeline.

Priority order:
  1. Focus Mode active  → UPLOADED (forced)
  2. Explicit doc cues  → UPLOADED
  3. Realtime patterns  → REALTIME  (→ Tavily + Groq)
  4. Groq classifier    → GENERAL vs RAG
  5. Enterprise cues    → ENTERPRISE_KB
  6. Default            → ONGC_KB
"""
from enum import Enum
from typing import Optional
import re


class IntentCategory(str, Enum):
    UPLOADED = "uploaded"
    ENTERPRISE_KB = "enterprise_kb"
    ONGC_KB = "ongc_kb"
    GENERAL = "general"
    REALTIME = "realtime"


_UPLOAD_EXPLICIT_PATTERNS = [
    r"\buploaded document(s)?\b",
    r"\battached file\b",
    r"\bthis document\b",
    r"\bthat document\b",
    r"\bthis pdf\b",
    r"\bthe pdf\b",
    r"\bin the file\b",
    r"\bin the document\b",
    r"\bin the pdf\b",
    r"\b[\w .-]+\.pdf\b",
    r"\b[\w .-]+\.docx\b",
    r"\b[\w .-]+\.txt\b",
    r"\baccording to (?:the )?(?:file|document|pdf)\b",
    r"\bpage \d+\b",
    r"\bchapter \d+\b",
    r"\bsection \d+\b",
    r"\btable of contents\b",
    r"\bocr\b",
]

_ENTERPRISE_KEYWORDS = [
    r"human resources",
    r"\bhr\b",
    r"procurement",
    r"purchase",
    r"vendor",
    r"tender",
    r"finance",
    r"budget",
    r"expense",
    r"travel policy",
    r"safety",
    r"compliance",
    r"disciplinary",
    r"leave policy",
    r"employee policy",
    r"circular",
    r"sop",
    r"standard operating procedure",
    r"company policy",
    r"approval",
    r"delegation of authority",
    r"\bhse\b",
    r"\bptw\b",
    r"permit to work",
    r"\bppe\b",
    r"protective equipment",
    r"incident reporting",
    r"emergency response",
    r"fire safety",
    r"hazard",
    r"risk assessment",
    r"workplace safety",
    r"recruitment",
    r"employee benefits",
    r"training",
    r"it policies",
    r"cyber",
    r"digital transformation",
    r"project management",
    r"quality assurance",
    r"governance",
    r"sustainability",
    r"environment",
    r"audit",
]

_ONGC_KEYWORDS = [
    r"\bongc\b",
    r"oil and natural gas",
    r"exploration",
    r"production",
    r"drilling",
    r"reservoir",
    r"offshore",
    r"onshore",
    r"wellhead",
    r"pipeline",
    r"petroleum",
    r"crude",
    r"natural gas",
    r"geology",
    r"asset",
    r"field",
    r"rig",
    r"seismic",
    r"well",
    r"upstream",
    r"hydrocarbon",
    r"basin",
    r"refinery",
    r"deepwater",
    r"subsea",
]

# Pronoun patterns that should resolve to the focused document
_PRONOUN_PATTERNS = [
    (r"\bit\b", "{doc}"),
    (r"\bthis\b", "{doc}"),
    (r"\bthat\b", "{doc}"),
    (r"\bthe document\b", "{doc}"),
    (r"\bthe pdf\b", "{doc}"),
    (r"\bthis file\b", "{doc}"),
    (r"\bthe uploaded file\b", "{doc}"),
    (r"\bthe file\b", "{doc}"),
    (r"\bthis document\b", "{doc}"),
]


def resolve_focus_context(question: str, focus_doc_name: str) -> str:
    """
    If a document is focused, resolve ambiguous pronouns/references to the doc name.
    E.g. "Summarise it" → "Summarise Unit 3 and 4 Question Bank.pdf"
         "Explain this" → "Explain Unit 3 and 4 Question Bank.pdf"
         "Give notes"   → "Give notes from Unit 3 and 4 Question Bank.pdf"

    If no pronoun is found but the question is very short (< 6 words),
    append document context at the end.
    """
    if not focus_doc_name:
        return question

    q = question.strip()
    q_lower = q.lower()
    replaced = False

    for pattern, replacement in _PRONOUN_PATTERNS:
        if re.search(pattern, q_lower):
            # Replace the match in the original-cased question
            q = re.sub(pattern, replacement.format(doc=focus_doc_name), q, flags=re.IGNORECASE)
            replaced = True

    # If no pronoun found and question doesn't already mention the doc,
    # but it's a short actionable instruction, append context
    if not replaced and focus_doc_name.lower() not in q_lower:
        word_count = len(q.split())
        # Short imperative phrases: "Give notes", "Generate MCQs", "List formulas", etc.
        if word_count <= 5:
            q = f"{q} from the document '{focus_doc_name}'"
        # Slightly longer but still likely about the doc
        elif word_count <= 10 and not any(
            re.search(pat, q_lower) for pat in _UPLOAD_EXPLICIT_PATTERNS
        ):
            q = f"{q} (referring to the document '{focus_doc_name}')"

    return q


def _match_keywords(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


async def classify_intent(question: str, focus_document_id: Optional[int] = None) -> IntentCategory:
    """Classify the retrieval scope before vector search.

    Routing priority:
      1. Explicit Focus Mode => uploaded document
      2. Explicit uploaded-document cues => uploaded document
      3. Realtime patterns => realtime (Tavily + Groq)
      4. Groq-based classifier => general vs corporate question
      5. Enterprise policy cues => enterprise KB scope
      6. Everything else => ONGC KB scope
    """
    if focus_document_id is not None:
        return IntentCategory.UPLOADED

    if _match_keywords(question, _UPLOAD_EXPLICIT_PATTERNS):
        return IntentCategory.UPLOADED

    # Check for real-time query BEFORE calling Groq (fast local check)
    from app.services.tavily import is_realtime_query
    if is_realtime_query(question):
        return IntentCategory.REALTIME

    # Call Groq classifier for hybrid routing
    from app.services.groq import classify_intent_groq
    groq_intent = await classify_intent_groq(question)

    if groq_intent == "GENERAL":
        return IntentCategory.GENERAL

    if _match_keywords(question, _ENTERPRISE_KEYWORDS):
        return IntentCategory.ENTERPRISE_KB

    return IntentCategory.ONGC_KB
