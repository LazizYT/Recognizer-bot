import hashlib
import logging
import pickle
from typing import Any

import redis

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self, redis_url: str = "redis://localhost:6379/0", conn=None):
        """Cache wrapper around a redis connection.

        Parameters
        - redis_url: URL used to create a redis client if `conn` is not provided
        - conn: optional redis connection instance (useful for tests)
        """
        if conn is not None:
            self.conn = conn
        else:
            self.conn = redis.from_url(redis_url)

    def _key(self, key: str) -> str:
        return f"tgocr:cache:{key}"

    def get(self, key: str):
        val = self.conn.get(self._key(key))
        if val is None:
            return None
        try:
            return pickle.loads(val)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        val = pickle.dumps(value)
        self.conn.set(self._key(key), val, ex=ttl)

    def exists(self, key: str) -> bool:
        return self.conn.exists(self._key(key)) == 1

    def delete(self, key: str):
        self.conn.delete(self._key(key))
