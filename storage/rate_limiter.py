import os
import time
import redis


class RateLimiter:
    def __init__(self, redis_url: str = None, max_per_minute: int = 15):
        redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.conn = redis.from_url(redis_url)
        self.max_per_minute = max_per_minute

    def allow(self, user_id: int) -> bool:
        key = f"tgocr:rate:{user_id}:{int(time.time() // 60)}"
        val = self.conn.incr(key)
        if val == 1:
            # set expire for the current minute
            self.conn.expire(key, 61)
        return val <= self.max_per_minute

    def remaining(self, user_id: int) -> int:
        key = f"tgocr:rate:{user_id}:{int(time.time() // 60)}"
        val = self.conn.get(key)
        if not val:
            return self.max_per_minute
        try:
            used = int(val)
        except Exception:
            used = 0
        return max(0, self.max_per_minute - used)
