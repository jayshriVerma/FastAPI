# middleware/rate_limit.py
import math
import time
import typing as t

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Lua script: atomically prune old timestamps, add current, return (count, oldest_score_or_nil)
# ARGV[1] = now (float)
# ARGV[2] = window (seconds)
# ARGV[3] = limit (int)
# Return: table [count, oldest_score]
LUA_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
-- prune
redis.call("ZREMRANGEBYSCORE", key, "-inf", now - window)
-- add this call with score = now and member = now|random to avoid collisions
local member = tostring(now) .. "-" .. tostring(math.random())
redis.call("ZADD", key, now, member)
-- set TTL slightly larger than window to allow automatic cleanup
redis.call("EXPIRE", key, math.ceil(window) + 2)
local count = redis.call("ZCARD", key)
local oldest = nil
if count > 0 then
  local arr = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
  if arr and #arr >= 2 then
    oldest = arr[2]
  end
end
return {tostring(count), tostring(oldest or "nil")}
"""


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed sliding-window rate limiter.
    - key: based on identifier (ip or header)
    - window_seconds: sliding window
    - max_calls: max calls allowed in window
    """

    def __init__(
        self,
        app,
        redis_client: Redis,
        *,
        max_calls: int = 100,
        window_seconds: int = 60,
        key_prefix: str = "rl:",
        identifier_header: str | None = None,  # if set, use this header as identifier
    ):
        super().__init__(app)
        self.redis = redis_client
        self.max_calls = int(max_calls)
        self.window = int(window_seconds)
        self.prefix = key_prefix
        self.header = identifier_header
        # we'll load the script once
        self._sha: str | None = None

    async def _ensure_script(self):
        if self._sha is None:
            self._sha = await self.redis.script_load(LUA_SCRIPT)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for docs and openapi paths
        # whitelist all swagger/redoc resources
        PUBLIC_PATHS = {
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
            "/swagger-ui-bundle.js",
            "/swagger-ui-init.js",
            "/swagger-ui.css",
        }
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        redis = request.app.state.redis
        if not hasattr(self, "_sha") or self._sha is None:
            self._sha = await redis.script_load(LUA_SCRIPT)
        identifier = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-KEY")
        print("API Key:", api_key)
        key = f"rl:{api_key}" if api_key else f"rl:{identifier}"
        print("Key:", key)

        now = (
            time.time()
        )  # use wall-clock seconds for keys (monotonic can be used but Redis needs comparable values)
        # Call Lua script atomically. ARGV: now, window, limit
        try:
            print("Redis key:", key)
            print("now:", now, type(now))
            print("window:", self.window, type(self.window))
            print("max_calls:", self.max_calls, type(self.max_calls))
            print("Connected Redis:", redis)
            result = await redis.evalsha(
                self._sha,
                keys=[key],
                args=[str(now), str(self.window), str(self.max_calls)],
            )
            # result is [count_str, oldest_str_or_nil]
            count = int(result[0])
            oldest = None if result[1] == "nil" else float(result[1])
        except Exception as e:
            # If script missing for some reason, try eval as fallback
            try:
                result = result = await redis.eval(
                    LUA_SCRIPT, 1, key, now, self.window, self.max_calls
                )
                count = int(result[0])
                oldest = None if result[1] == "nil" else float(result[1])
            except Exception as ee:
                # Redis failure -> fail-open (or fail-closed depending on policy)
                return JSONResponse(
                    {"detail": "rate limiter unavailable"}, status_code=503
                )

        if count > self.max_calls:
            # compute retry_after: time until oldest + window - now
            retry_after = 0
            if oldest is not None:
                remaining = (oldest + self.window) - now
                retry_after = max(0, math.ceil(remaining))
            headers = {"Retry-After": str(retry_after)}
            return JSONResponse(
                {"detail": "Too Many Requests", "retry_after": retry_after},
                status_code=429,
                headers=headers,
            )

        # allowed
        response = await call_next(request)
        return response
