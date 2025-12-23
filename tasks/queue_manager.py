import os
import redis   # pyright: ignore[reportMissingImports]
from rq import Queue   # pyright: ignore[reportMissingImports]

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_conn = redis.from_url(redis_url)
q = Queue("default", connection=redis_conn)


def enqueue_job(func, *args, **kwargs):
    job = q.enqueue(func, *args, **kwargs)
    return job
