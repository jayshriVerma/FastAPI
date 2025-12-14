import json
from typing import Dict, Optional

import redis.asyncio as redis

from app.repositories.interface import UserRepository


class RedisUserRepository(UserRepository):
    """Redis-Based Async Implementation of UserRepository Interface"""

    def __init__(self, *, redis_url: str):
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

    async def add_tag(self, username: str, tags: list[str]) -> Dict:
        key = self._user_key(username)

        data = await self._redis.get(key)
        if not data:
            raise KeyError("User not found")

        user = json.loads(data)
        user["tags"] = tags

        await self._redis.set(key, json.dumps(user))
        return user

    async def list_users(self) -> Dict[str, Dict]:
        users: Dict[str, Dict] = {}
        # use SCAN to iterate over keys(does not block Redis like KEYS)
        cursor = "0"

        while True:
            cursor, keys = await self._redis.scan(
                cursor=cursor, match="user:*", count=100
            )
            for key in keys:
                value = await self._redis.get(key)
                if value:
                    username = key.split(":", 1)[1]
                    users[username] = json.loads(value)

            if cursor == 0:  # scan complete
                break

        return users

    async def delete_user(self, username: str) -> None:
        key = self._user_key(username)
        result = await self._redis.delete(key)
        if result == 0:
            raise KeyError("User not found")
