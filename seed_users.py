import asyncio
from app.repositories.user_repo import RedisUserRepository
from datetime import datetime, timezone
from app.core.config import settings


REDIS_URL = settings.REDIS_URL

async def seed():
    repo = RedisUserRepository(redis_url= REDIS_URL)

    for i in range(1000_000):
        username = f"user1_{i}"
        user = {
            "username": username,
            "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await repo.create_user(user)
        except KeyError:
            pass  # user already exists

    print("Inserted 1000 users")


if __name__ == "__main__":
    asyncio.run(seed())
