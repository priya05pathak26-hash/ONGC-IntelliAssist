import hashlib
import math
import re
from collections import Counter
from functools import lru_cache


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]*")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "what", "when", "where", "which", "who", "why", "with", "write",
}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOPWORDS]


@lru_cache(maxsize=8192)
def embedding(text: str) -> dict[str, float]:
    counts = Counter(tokenize(text))
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {key: value / norm for key, value in counts.items()}


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def stable_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chunk_text(text: str, size: int = 1500, overlap: int = 350) -> list[str]:
    """
    Split text into overlapping chunks.
    Uses RecursiveCharacterTextSplitter-style sizing: chunk_size=1500, chunk_overlap=350.
    Tries to split at sentence boundaries where possible to preserve semantic context.
    Never creates meaningless tiny chunks.
    """
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        # Try to end at a sentence boundary (. ! ?) within last 20% of chunk
        if end < len(clean):
            boundary_search_start = max(start, end - int(size * 0.20))
            boundary = max(
                clean.rfind(". ", boundary_search_start, end),
                clean.rfind("! ", boundary_search_start, end),
                clean.rfind("? ", boundary_search_start, end),
                clean.rfind("\n", boundary_search_start, end),
            )
            if boundary > start:
                end = boundary + 1
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return chunks


def deduplicate_chunks(chunks: list[str], similarity_threshold: float = 0.92) -> list[str]:
    """
    Remove near-duplicate chunks using cosine similarity.
    Preserves ordering.
    """
    if not chunks:
        return chunks
    unique: list[str] = []
    unique_embeddings: list[dict[str, float]] = []
    for chunk in chunks:
        emb = embedding(chunk)
        is_dup = any(
            cosine(emb, existing) >= similarity_threshold
            for existing in unique_embeddings
        )
        if not is_dup:
            unique.append(chunk)
            unique_embeddings.append(emb)
    return unique


def detect_domain(question: str) -> str:
    q = question.lower()
    domains = {
        "Human Resources": ["hr", "leave", "benefit", "employee", "performance", "recruitment", "training"],
        "Finance & Accounts": ["finance", "budget", "accounting", "tax", "invoice", "audit"],
        "Procurement": ["procurement", "purchase", "vendor", "tender", "contract"],
        "HSE": ["hse", "safety", "fire", "ppe", "emergency", "incident"],
        "Exploration & Drilling": ["exploration", "drilling", "reservoir", "well", "seismic"],
        "Production & Operations": ["production", "operations", "refinery", "maintenance"],
        "IT & Cybersecurity": ["it", "password", "cyber", "security", "phishing", "network"],
        "Corporate Governance": ["governance", "legal", "compliance", "board", "policy"],
        "Sustainability & CSR": ["sustainability", "csr", "environment", "community"],
    }
    for domain, keywords in domains.items():
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, q):
                return domain
    return "ONGC Overview"
