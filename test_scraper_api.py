import asyncio
import httpx
import json

async def test_scraper_workflow():
    print("==========================================")
    print(" RUNNING SCRAPER & SSE LOGGER TEST")
    print("==========================================")

    url_base = "http://127.0.0.1:8000"
    
    # We need to run the FastAPI app concurrently so we can make HTTP requests to it.
    # To do this, we'll start uvicorn inside the python process as a task or run it locally.
    # But wait! We can just import and use httpx's AsyncClient with ASGI transport!
    # Yes! httpx supports direct testing of ASGI apps without running a real server!
    # Let's import the app and use httpx.AsyncClient(transport=httpx.ASGITransport(app=app))
    from app import app
    
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Fetch current status
        resp = await client.get("/api/scrape/status")
        print(f"1. Initial status: {resp.json()}")
        assert resp.json()["is_running"] is False
        
        # 2. Get Search configs to find a valid config ID
        resp = await client.get("/api/search-configs")
        configs = resp.json()
        assert len(configs) > 0
        config_id = configs[0]["id"]
        print(f"2. Found Search Config ID: {config_id} for sector: {configs[0]['sector_name']}")
        
        # 3. Connect to the SSE stream and listen concurrently
        print("\n3. Listening to Server-Sent Events logs stream concurrently...")
        
        # We define a reader task
        async def sse_reader():
            try:
                # We open a stream connection to /api/scrape/stream
                # Note: httpx stream() works nicely for SSE testing
                async with client.stream("GET", "/api/scrape/stream") as response:
                    print("   [SSE Connect Success]")
                    async for line in response.iter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            log_entry = json.loads(data_str)
                            print(f"   [Real-time Log] {log_entry['timestamp']} | {log_entry['level'].upper()} | {log_entry['message']}")
                            
                            # Break if we get stop log or after a few updates
                            if "durduruldu" in log_entry['message'] or "tamamlandı" in log_entry['message']:
                                break
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"   [SSE Reader Error]: {e}")
                
        reader_task = asyncio.create_task(sse_reader())
        await asyncio.sleep(0.5) # Give reader a moment to connect
        
        # 4. Trigger start scraper
        print(f"\n4. Triggering start scraping for config ID: {config_id}...")
        resp = await client.post("/api/scrape/start", json={"config_id": config_id})
        print(f"   > Start Response: {resp.json()}")
        assert resp.status_code == 200
        
        # Wait a few seconds to let it run and log
        print("\n5. Waiting 4 seconds for scraping logs...")
        await asyncio.sleep(4.0)
        
        # 5. Check status while running
        resp = await client.get("/api/scrape/status")
        status_running = resp.json()
        print(f"\n6. Running status: {status_running}")
        
        # 6. Stop scraping
        print("\n7. Triggering stop scraping...")
        resp = await client.post("/api/scrape/stop")
        print(f"   > Stop Response: {resp.json()}")
        assert resp.status_code == 200
        
        # Wait for the reader to output the cancellation log
        await asyncio.sleep(1.0)
        reader_task.cancel()
        
        # Final status check
        resp = await client.get("/api/scrape/status")
        print(f"\n8. Final status: {resp.json()}")
        assert resp.json()["is_running"] is False
        print("\n==========================================")
        print(" SCRAPER & SSE TEST COMPLETED SUCCESSFULLY!")
        print("==========================================")

if __name__ == "__main__":
    asyncio.run(test_scraper_workflow())
