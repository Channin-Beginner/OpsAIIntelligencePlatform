from functools import lru_cache

import redis

from app.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_settings()
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password_or_none,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    client.ping()
    return client


def check_redis() -> bool:
    try:
        get_redis_client().ping()
        return True
    except redis.RedisError:
        return False
