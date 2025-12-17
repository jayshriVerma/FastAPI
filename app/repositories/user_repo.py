import json
from datetime import datetime, timedelta, timezone
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
        if result == "0":
            raise KeyError("User not found")

    async def delete_all(self) -> None:
        cursor = 0

        while True:
            cursor, keys = await self._redis.scan(
                cursor=cursor, match="user:*", count=100
            )
            if keys:
                await self._redis.delete(*keys)
            # Redis returns cursor as string "0", not int 0
            if cursor == 0:  # scan complete
                break

    async def delete_inactive_users(self, inactive_since: float) -> int:
        """Delete users who have not been active since the given timestamp.
        Returns the number of users deleted.
        """
        deleted_count = 0
        cursor = 0

        while True:
            cursor, keys = await self._redis.scan(
                cursor=cursor, match="user:*", count=100
            )
            for key in keys:
                value = await self._redis.get(key)
                if value:
                    user = json.loads(value)
                    raw = user.get("last_active")

                    if (
                        raw is None
                    ):  # Works with: old ISO strings,new float timestamps,missing values
                        last_active = 0.0
                    elif isinstance(raw, (int, float)):
                        last_active = float(raw)
                    else:
                        # ISO string → timestamp
                        last_active = datetime.fromisoformat(raw).timestamp()

                    if last_active < inactive_since:
                        await self._redis.delete(key)
                        deleted_count += 1

            if cursor == 0:  # scan complete
                break

        return deleted_count

    async def touch_user(self, username: str) -> None:
        user = await self.get_user(username)
        if not user:
            return

        user["last_active"] = datetime.now(timezone.utc).isoformat()
        await self._redis.set(self._user_key(username), json.dumps(user))
