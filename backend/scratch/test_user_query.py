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

        q = "Compare ONGC's revenue for FY 2022-23, FY 2023-24 and FY 2024-25."
        print(f"\nTesting Question: {q}")
        async with client.stream(
            "POST", "/api/chat/stream",
            headers=headers,
            json={"question": q, "session_id": None, "mode": "auto", "focus_document_id": None},
        ) as resp:
            async for line in resp.aiter_lines():
                if line.strip():
                    try:
                        event = json.loads(line)
                        if event.get("event") == "token":
                            print(event.get("text"), end="", flush=True)
                        elif event.get("event") == "done":
                            print(f"\n[DONE] {event.get('source')}")
                    except:
                        pass

asyncio.run(test())
