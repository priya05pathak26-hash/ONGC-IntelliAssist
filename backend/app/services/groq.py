import json
from collections.abc import AsyncIterator
import httpx

from app.config import get_settings

settings = get_settings()


async def call_groq_chat(messages: list[dict], stream: bool = False):
    """
    Constructs components for the Groq API call.
    """
    api_key = settings.groq_api_key
    if api_key:
        api_key = api_key.strip()
    if not api_key:
        import os
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            api_key = api_key.strip()

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured. Please define it in your environment or .env file.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": 0.2,
        "stream": stream
    }
    url = "https://api.groq.com/openai/v1/chat/completions"
    return url, headers, payload


async def query_groq(messages: list[dict]) -> str:
    """
    Sends a chat completion request to Groq and returns the text response.
    """
    try:
        url, headers, payload = await call_groq_chat(messages, stream=False)
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as exc:
        raise RuntimeError(f"Failed to query Groq: {exc}") from exc


async def query_groq_with_tavily_context(question: str, tavily_context: str, history_messages: list[dict]) -> str:
    """
    Call Groq with Tavily search results as grounded context.
    Never lets Groq answer from its own memory for real-time queries.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log for debugging
    logger.info(f"=== TAVILY GROUNDING DEBUG ===")
    logger.info(f"Question: {question}")
    logger.info(f"Tavily Context: {tavily_context}")
    
    system_prompt = (
        "You are answering using LIVE WEB SEARCH RESULTS from Tavily.\n\n"
        "CRITICAL INSTRUCTIONS - READ CAREFULLY:\n"
        "1. The search results below are the ONLY trusted source of information.\n"
        "2. You MUST answer ONLY from the provided search results.\n"
        "3. NEVER answer from your internal memory, training data, or pre-2024 knowledge.\n"
        "4. If the search results contradict your internal knowledge, ALWAYS trust the search results.\n"
        "5. If the search results do not contain a clear answer, explicitly state: 'The search results do not contain enough information to answer this question.'\n"
        "6. Do NOT fabricate, guess, or use any information not present in the search results.\n"
        "7. Do NOT include URLs or source links in your answer body. Just provide the factual information.\n"
        "8. Be precise and factual based EXACTLY on what the search results say.\n\n"
        f"LIVE WEB SEARCH RESULTS:\n{tavily_context}\n\n"
        "Answer the user's question using ONLY the information above. If the search results provide the answer, state it clearly. If they don't, say so explicitly."
    )
    messages = [{"role": "system", "content": system_prompt}]
    # Include last 4 history messages for conversational context
    for msg in history_messages[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})
    
    logger.info(f"Groq Prompt: {messages}")
    
    response = await query_groq(messages)
    
    logger.info(f"Groq Response: {response}")
    logger.info(f"=== END TAVILY GROUNDING DEBUG ===")
    
    return response


async def stream_groq(messages: list[dict]) -> AsyncIterator[str]:
    """
    Sends a chat completion request to Groq and streams the response text.
    """
    try:
        url, headers, payload = await call_groq_chat(messages, stream=True)
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise RuntimeError(f"Groq API returned HTTP {response.status_code}: {error_body.decode('utf-8')}")

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue
    except Exception as exc:
        raise RuntimeError(f"Error streaming from Groq: {exc}") from exc


async def stream_groq_with_tavily_context(question: str, tavily_context: str, history_messages: list[dict]) -> AsyncIterator[str]:
    """
    Stream Groq response grounded with Tavily search results.
    """
    system_prompt = (
        "You are ONGC IntelliAssist, a helpful AI assistant.\n"
        "You have been given live web search results from Tavily to answer the user's question.\n"
        "Answer ONLY using the provided search results below. Do NOT use your training knowledge.\n"
        "If the search results do not contain a clear answer, say so honestly.\n"
        "Format your answer clearly with:\n"
        "- A direct answer at the top\n"
        "- Supporting details with bullet points\n"
        "- Source references where available\n\n"
        f"Live Web Search Results:\n{tavily_context}"
    )
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history_messages[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})
    async for token in stream_groq(messages):
        yield token


async def classify_intent_groq(question: str) -> str:
    """
    Quickly classifies if the user's question is related to ONGC/uploaded documents (RAG)
    or is a general question/greetings (GENERAL).
    """
    system_prompt = (
        "You are an intent classifier for an enterprise chatbot.\n"
        "Classify the user's question as either 'RAG' or 'GENERAL'.\n\n"
        "Respond with 'RAG' if the question is related to any of:\n"
        "- Uploaded files, documents, PDFs, DOCX, TXT\n"
        "- ONGC (Oil and Natural Gas Corporation) or oil/gas industry operations/drilling/reservoir/rigs\n"
        "- HSE (Health, Safety, and Environment), safety policies, PTW, PPE\n"
        "- HR policies, leave policy, payroll, employee benefits, finance, procurement, vendor tenders, corporate guidelines\n"
        "- Technical documents, engineering, geology, seismology\n\n"
        "Respond with 'GENERAL' if the question is NOT related to ONGC or corporate documents, such as:\n"
        "- General knowledge (e.g. 'Who is the President of the US?', capitals, geography)\n"
        "- Coding, programming, Python, HTML, algorithms, technology\n"
        "- General mathematics, weather, news, current affairs, sports\n"
        "- General greetings, friendly chatter, conversation (e.g. 'hi', 'how are you', 'thank you')\n\n"
        "Reply ONLY with the single word 'RAG' or 'GENERAL'. Do not write punctuation or extra explanations."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    try:
        res = await query_groq(messages)
        res_cleaned = res.strip().upper()
        if "RAG" in res_cleaned:
            return "RAG"
        elif "GENERAL" in res_cleaned:
            return "GENERAL"
        return "RAG"  # Default fallback
    except Exception:
        return "FALLBACK"
