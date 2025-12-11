import asyncio

import redis.asyncio as redis


async def test():
    client = redis.from_url("redis://localhost:6379", decode_responses=True)
    await client.set("test", "ok")
    value = await client.get("test")
    print(value)


asyncio.run(test())
# Expected output: ok
# If this prints ok → your Redis + networking + Python client are all PERFECT.
# FastAPI  → Redis TCP socket → Memory store
