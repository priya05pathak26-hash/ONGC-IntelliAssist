import json
from dataclasses import dataclass
from pathlib import Path

from app.services.text_tools import chunk_text, cosine, detect_domain, embedding


KB_ROOT = Path(__file__).resolve().parents[2] / "knowledge_base"


@dataclass
class KnowledgeMatch:
    domain: str
    source_file: str
    score: float
    chunk: str


class KBVectorCache:
    _cached_chunks = None

    @classmethod
    def get_chunks(cls):
        if cls._cached_chunks is None:
            cls.refresh()
        return cls._cached_chunks

    @classmethod
    def refresh(cls):
        records = load_knowledge_chunks()
        cls._cached_chunks = []
        for record in records:
            cls._cached_chunks.append({
                "domain": record.domain,
                "source_file": record.source_file,
                "chunk": record.chunk,
                "embedding": embedding(record.chunk)
            })


def load_knowledge_chunks() -> list[KnowledgeMatch]:
    records: list[KnowledgeMatch] = []
    for path in KB_ROOT.rglob("*.md"):
        domain = path.parent.name.replace("_", " ").title()
        text = path.read_text(encoding="utf-8")
        for chunk in chunk_text(text):
            records.append(KnowledgeMatch(domain=domain, source_file=path.name, score=0, chunk=chunk))
    return records


def search_knowledge(question: str, threshold: float = 0.24) -> KnowledgeMatch | None:
    query = embedding(question)
    domain_hint = detect_domain(question)
    best: KnowledgeMatch | None = None
    
    chunks = KBVectorCache.get_chunks()
    for record in chunks:
        score = cosine(query, record["embedding"])
        if record["domain"].lower() in domain_hint.lower() or domain_hint.lower() in record["domain"].lower():
            score += 0.08
        if not best or score > best.score:
            best = KnowledgeMatch(record["domain"], record["source_file"], score, record["chunk"])
            
    return best if best and best.score >= threshold else None


def citation_json(source: str, score: float | None, chunk: str | None, file_name: str | None = None) -> str:
    return json.dumps(
        [{"source": source, "similarity_score": score, "retrieved_chunk": None, "file_name": file_name}],
        ensure_ascii=False,
    )
