from enum import Enum
from typing import Optional
import re


class IntentCategory(str, Enum):
    UPLOADED = "uploaded"
    ENTERPRISE_KB = "enterprise_kb"
    ONGC_KB = "ongc_kb"
    GENERAL_KNOWLEDGE = "general_knowledge"
    GENERAL_AI = "general_ai"


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

_GENERAL_KNOWLEDGE_PATTERNS = [
    r"\bwho is\b",
    r"\bwhat is\b",
    r"\bwhat are\b",
    r"\bwhere is\b",
    r"\bwhen was\b",
    r"\bwhy is\b",
    r"\bcapital of\b",
    r"\bprime minister\b",
    r"\bpresident of\b",
    r"\bnewton'?s laws\b",
    r"\bwhat is python\b",
    r"\bexplain python\b",
    r"\bwho wrote\b",
    r"\bhow many\b",
]


def _match_keywords(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def classify_intent(question: str, focus_document_id: Optional[int] = None) -> IntentCategory:
    """Classify the user's question before any retrieval happens.

    Routing priority:
      1. Explicit Focus Mode => uploaded document
      2. Explicit uploaded-document cues => uploaded document
      3. ONGC or enterprise policy cues
      4. General knowledge / general AI fallback
    """

    if focus_document_id is not None:
        return IntentCategory.UPLOADED

    if _match_keywords(question, _UPLOAD_EXPLICIT_PATTERNS):
        return IntentCategory.UPLOADED

    if _match_keywords(question, _ONGC_KEYWORDS):
        return IntentCategory.ONGC_KB

    if _match_keywords(question, _ENTERPRISE_KEYWORDS):
        return IntentCategory.ENTERPRISE_KB

    if _match_keywords(question, _GENERAL_KNOWLEDGE_PATTERNS):
        return IntentCategory.GENERAL_KNOWLEDGE

    return IntentCategory.GENERAL_AI
