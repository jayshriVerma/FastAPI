import json
from typing import Dict, Optional

import redis.asyncio as redis

from app.repositories.interface import UserRepository


class RedisUserRepository(UserRepository):
    """Redis-Based Async Implementation of UserRepository Interface"""

    def __init__(self, redis_url: str):
        self._redis = redis.from_url(redis_url, decode_responses=True)

    def _user_key(self, username: str) -> str:
        return f"user:{username}"

    async def create_user(self, user: Dict) -> None:
        key = self._user_key(user["username"])

        # SETNX → only set if not exists (atomic)
        created = await self._redis.setnx(key, json.dumps(user))

        if not created:
            raise ValueError("User already exists")

    async def get_user(self, username: str) -> Optional[Dict]:
        key = self._user_key(username)
        data = await self._redis.get(key)

        if not data:
            return None

        return json.loads(data)

    async def add_tag(self, username: str, tag: str) -> Dict:
        key = self._user_key(username)

        data = await self._redis.get(key)
        if not data:
            raise KeyError("User not found")

        user = json.loads(data)
        user["tags"].append(tag)

        await self._redis.set(key, json.dumps(user))
        return user
