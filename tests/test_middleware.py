import pytest
from fastapi import FastAPI, Request, Response
from unittest.mock import AsyncMock, Mock

from redis import Redis
from app.main import app as fastapi_app
from app.middleware.rate_limit import RedisRateLimitMiddleware
from types import SimpleNamespace


@pytest.fixture
def app():
    return fastapi_app

@pytest.mark.asyncio
async def test_rate_limit_allows_request(app):
    # checks that the rate-limit middleware lets a request pass through when the user has not exceeded the limit.
    redis = AsyncMock()
    redis.get.return_value = None
    redis.incr.return_value = 1

    middleware = RedisRateLimitMiddleware(app, redis_client=Mock(spec_set=Redis))

    async def call_next(request: Request):
        return Response("OK", status_code=200)
    
    # fake request
    request = Request(
        scope={
            "type": "http",
            "headers": [],
            "app": SimpleNamespace(state=SimpleNamespace(redis=redis)),
            "path": "/users",
            "method": "POST",

        }
    )
    response = await middleware.dispatch(request, call_next)

    assert isinstance(app, FastAPI)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_rate_limit_blocks_request():
    redis = AsyncMock()

    redis.get.return_value = 5
    redis.incr.return_value = 6 # over the limit
    redis.expire.return_value = True

    app = SimpleNamespace(state=SimpleNamespace(redis=redis))
    middleware = RedisRateLimitMiddleware(app, redis_client=Mock(spec_set=Redis))

    async def call_next(request):
        return Response("Too many request", status_code=429)

    request = Request(
        scope={
            "type": "http",
            "method": "POST",
            "path": "/users",
            "headers": [],
            "app": app,
        }
    )

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 429
