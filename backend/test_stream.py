import httpx
import asyncio
import json

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=120) as client:
        login_resp = await client.post("/api/auth/login", json={
            "email": "admin@ongc.com",
            "password": "Admin@12345"
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        questions = [
            "Compare total income for the last three years",
            "What is the capital of France?",
            "What is ONGC's safety policy?",
        ]
        for q in questions:
            print(f"\n{'='*60}")
            print(f"Q: {q}")
            print(f"{'='*60}")
            async with client.stream(
                "POST", "/api/chat/stream",
                headers=headers,
                json={"question": q, "session_id": None, "mode": "auto", "focus_document_id": None},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            event = json.loads(line)
                            ev = event.get("event", "?")
                            if ev == "token":
                                print(event.get("text", ""), end="", flush=True)
                            elif ev == "error":
                                print(f"\n[ERROR] {event}")
                            elif ev == "done":
                                print(f"\n[DONE] source={event.get('source')}")
                            elif ev == "status":
                                print(f"[{ev}] {event.get('message', '')}")
                        except:
                            pass

asyncio.run(test())
