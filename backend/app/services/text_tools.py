import hashlib
import math
import re
from collections import Counter
from functools import lru_cache


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]*")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


@lru_cache(maxsize=4096)
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


def chunk_text(text: str, size: int = 950, overlap: int = 140) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        chunks.append(clean[start:end].strip())
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks


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
        if any(keyword in q for keyword in keywords):
            return domain
    return "ONGC Overview"
