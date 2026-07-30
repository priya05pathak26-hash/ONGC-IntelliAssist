"""
Tavily real-time web search service for ONGC IntelliAssist.

Used for current-affairs questions that cannot be answered from FAISS/KB/Ollama:
  - Current heads of state / elections
  - Latest news, stock prices, weather
  - Sports results
  - Recent events (within last few months)
"""

import re
import httpx

from app.config import get_settings

settings = get_settings()

# ── Realtime query classifier ──────────────────────────────────────────────────

_REALTIME_PATTERNS = [
    r"\bcurrent\b",
    r"\blatest\b",
    r"\btoday\b",
    r"\bright now\b",
    r"\bthis year\b",
    r"\bthis week\b",
    r"\bthis month\b",
    r"\bnews\b",
    r"\bbreaking\b",
    r"\brecent\b",
    r"\brecentl\w+\b",
    r"\bweather\b",
    r"\bstock\b",
    r"\bmarket\b",
    r"\bprice\b",
    r"\belection\b",
    r"\bwho is the president\b",
    r"\bwho is the prime minister\b",
    r"\bwho is the ceo\b",
    r"\bwho is the chairman\b",
    r"\bwho is currently\b",
    r"\bwhat is the current\b",
    r"\bsports\b",
    r"\bscore\b",
    r"\bmatch\b",
    r"\bcricket\b",
    r"\bfootball\b",
    r"\bipl\b",
    r"\bworldcup\b",
    r"\bworld cup\b",
    r"\bai update\b",
    r"\bai news\b",
    r"\bchatgpt\b",
    r"\bgemini\b",
    r"\bwho won\b",
    r"\bwhat happened\b",
    r"\b202[4-9]\b",           # years 2024-2029
    r"\bjanuary|february|march|april|may|june|july|august|september|october|november|december\b",
]

# Questions that mention ONGC or enterprise context are NOT realtime
_ONGC_OVERRIDE_PATTERNS = [
    r"\bongc\b",
    r"\bhse\b",
    r"\bptw\b",
    r"\bppe\b",
    r"\bprocurement\b",
    r"\bleave policy\b",
    r"\bfinance\b",
    r"\bdrilling\b",
    r"\breservoir\b",
    r"\bexploration\b",
    r"\bthe document\b",
    r"\bthe pdf\b",
    r"\bthis document\b",
    r"\bthe file\b",
    r"\buploaded\b",
]


def is_realtime_query(question: str) -> bool:
    """Return True if the question needs live web data from Tavily."""
    q = question.lower()
    # If it's explicitly about ONGC/corporate knowledge, never route to Tavily
    if any(re.search(pat, q) for pat in _ONGC_OVERRIDE_PATTERNS):
        return False
    return any(re.search(pat, q) for pat in _REALTIME_PATTERNS)


# ── Tavily API call ────────────────────────────────────────────────────────────

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


async def search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """
    Call Tavily search API and return a list of result dicts.
    Each dict has: title, url, content, score, published_date.
    Returns empty list on error or missing key.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    api_key = settings.tavily_api_key
    if not api_key or api_key.startswith("tvly-dev-REPLACE"):
        logger.warning("Tavily API key not configured")
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "topic": "general",
        "include_answer": True,
        "include_raw_content": True,
        "max_results": max_results,
        "days": 7,  # Search recent content
    }
    
    logger.info(f"Tavily Search Query: {query}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TAVILY_SEARCH_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Tavily Raw Response: {data}")
            
            results = data.get("results", [])
            answer = data.get("answer", "")
            
            logger.info(f"Tavily Answer: {answer}")
            logger.info(f"Tavily Results Count: {len(results)}")
            
            formatted_results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                    "published_date": r.get("published_date", ""),
                    "tavily_answer": answer if idx == 0 else "",
                }
                for idx, r in enumerate(results)
            ]
            
            logger.info(f"Formatted Tavily Results: {formatted_results}")
            
            return formatted_results
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


def format_tavily_context(results: list[dict]) -> str:
    """
    Convert Tavily search results into a grounded context string for Groq.
    Extracts full content including title, content, snippet, and published date.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not results:
        logger.warning("No Tavily results to format")
        return ""
    
    parts = []
    
    # Include the Tavily synthesized answer first if present
    if results[0].get("tavily_answer"):
        parts.append(f"=== TAVILY SYNTHESIZED ANSWER ===\n{results[0]['tavily_answer']}\n")
    
    # Add detailed search results
    for idx, r in enumerate(results[:5]):
        title = r.get("title", "")
        content = r.get("content", "").strip()
        url = r.get("url", "")
        published_date = r.get("published_date", "")
        
        if content:
            part = f"=== SOURCE {idx + 1} ===\n"
            part += f"Title: {title}\n"
            if published_date:
                part += f"Published: {published_date}\n"
            part += f"Content: {content}\n"
            part += f"URL: {url}"
            parts.append(part)
    
    context = "\n\n".join(parts)
    logger.info(f"Formatted Tavily Context: {context[:500]}...")
    
    return context
