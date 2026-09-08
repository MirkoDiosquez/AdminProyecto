"""
Cliente Redis — usado EXCLUSIVAMENTE como cache de Analytics (read-through).
No reemplaza a PostgreSQL ni a RabbitMQ.
"""
import redis
from app.config import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True,
)


def get_redis() -> redis.Redis:
    return redis_client
