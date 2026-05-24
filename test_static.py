import asyncio
import httpx
from app import app

async def test_static_routes():
    t = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=t, base_url="http://test") as client:
        r1 = await client.get("/")
        r2 = await client.get("/style.css")
        r3 = await client.get("/app.js")
        print("GET /  :", r1.status_code, f"({len(r1.text)} bytes)")
        print("GET /style.css :", r2.status_code, f"({len(r2.text)} bytes)")
        print("GET /app.js    :", r3.status_code, f"({len(r3.text)} bytes)")
        
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200
        print("All static endpoints served successfully!")

if __name__ == "__main__":
    asyncio.run(test_static_routes())
