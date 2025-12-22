import json
from datetime import datetime

import redis


class RedisUserRepositorySync:
    def __init__(self):
        self.redis = redis.Redis(host="localhost", port=6379, decode_responses=False)

    def delete_inactive_users(self, inactive_since: float) -> int:
        """
        Delete users whose last_active timestamp is older than inactive_since.
        inactive_since: Unix timestamp (float)
        """
        deleted_count = 0
        cursor = 0

        while True:
            cursor, keys = self.redis.scan(cursor=cursor, match="user:*", count=100)

            for key in keys:
                value = self.redis.get(key)
                if not value:
                    continue

                user = json.loads(value.decode("utf-8"))
                raw = user.get("last_active")

                if raw is None:
                    last_active = 0.0
                elif isinstance(raw, (int, float)):
                    last_active = float(raw)
                else:
                    # ISO string → timestamp
                    last_active = datetime.fromisoformat(raw).timestamp()

                if last_active < inactive_since:
                    self.redis.delete(key)
                    deleted_count += 1

            if cursor == 0:
                break

        return deleted_count
