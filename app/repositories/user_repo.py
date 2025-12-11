import asyncio
from typing import Dict, Optional

from app.repositories.interface import UserRepository


class InMemoryUserRepository(UserRepository):
    """In-Memory Async Implementation of UserRepository Interface"""

    def __init__(self):
        self._db: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create_user(self, user: Dict) -> None:
        async with self._lock:
            if user["username"] in self._db:
                raise ValueError("User already exists")
            self._db[user["username"]] = user

    async def get_user(self, username: str) -> Optional[Dict]:
        async with self._lock:
            return self._db.get(username)

    async def add_tag(self, username: str, tag: str) -> Dict:
        async with self._lock:
            user = self._db.get(username)
            if not user:
                raise KeyError("User not found")
            user["tags"].append(tag)
            return user
