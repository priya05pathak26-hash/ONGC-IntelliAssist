import httpx
import asyncio

async def test():
    try:
        import os
        api_key = os.environ.get("GROQ_API_KEY", "")
        client = httpx.AsyncClient(timeout=15)
        r = await client.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': 'Hello'}],
                'max_tokens': 10
            }
        )
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:500]}")
        await client.aclose()
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())
