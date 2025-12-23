import fakeredis
import os
import redis
from storage.rate_limiter import RateLimiter


def test_rate_limiter_allow_and_remaining(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/0')
    # monkeypatch the redis.from_url used in RateLimiter
    monkeypatch.setattr(redis, 'from_url', lambda url: fake)

    rl = RateLimiter(max_per_minute=3)

    user_id = 123
    assert rl.allow(user_id)
    assert rl.allow(user_id)
    assert rl.allow(user_id)
    # fourth should be blocked
    assert not rl.allow(user_id)
    rem = rl.remaining(user_id)
    assert rem == 0
