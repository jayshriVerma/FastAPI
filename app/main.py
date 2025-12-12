from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.routes import health_router
from app.api.routes import router as user_router
from app.middleware.rate_limit import RedisRateLimitMiddleware
from settings import settings

app = FastAPI()
app.include_router(user_router)  # HAS AUTH
app.include_router(health_router)  # NO AUTH


REDIS_URL = settings.redis_url

# create redis client at module level (safe for single-process dev)
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


# If running with --reload or multiple workers, initialize Redis client on an app startup/close event
@app.on_event("startup")
async def startup_event():
    app.state.redis = Redis.from_url(REDIS_URL, decode_responses=True)


@app.on_event("shutdown")
async def shutdown_event():
    redis_client = getattr(app.state, "redis", None)
    if redis_client:
        await redis_client.close()


app.add_middleware(
    RedisRateLimitMiddleware, redis_client=redis_client, max_calls=5, window_seconds=10
)
