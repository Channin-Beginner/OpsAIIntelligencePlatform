import logging
from functools import lru_cache

import redis

from app.config import get_settings

logger = logging.getLogger("ops.redis")


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
    try:
        client.ping()
    except redis.RedisError:
        logger.exception(
            "Redis connection failed host=%s port=%s db=%s",
            settings.redis_host,
            settings.redis_port,
            settings.redis_db,
        )
        raise
    return client


def check_redis() -> bool:
    try:
        get_redis_client().ping()
        return True
    except redis.RedisError:
        logger.warning(
            "Redis health check failed host=%s port=%s",
            get_settings().redis_host,
            get_settings().redis_port,
        )
        return False