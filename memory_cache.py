import logging
import os
from upstash_redis import Redis

logger = logging.getLogger(__name__)

class MemoryCache:
    _redis = None

    @classmethod
    def _get_redis(cls):
        if cls._redis is None:
            url = os.getenv("UPSTASH_REDIS_REST_URL")
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
            if not url or not token:
                logger.error("Upstash Redis credentials not configured in .env")
                return None
            cls._redis = Redis(url=url, token=token)
        return cls._redis

    @classmethod
    def get(cls, key):
        try:
            redis = cls._get_redis()
            if redis is None:
                return None
            value = redis.get(key)
            if value is not None:
                logger.info(f"Cache HIT: {key}")
                return value
            logger.info(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Upstash Redis GET error for {key}: {e}")
            return None

    @classmethod
    def setex(cls, name, time, value):
        try:
            redis = cls._get_redis()
            if redis is None:
                return
            redis.setex(name=name, seconds=time, value=value)
            logger.info(f"Cache SET: {name} (TTL: {time}s)")
        except Exception as e:
            logger.error(f"Upstash Redis SETEX error for {name}: {e}")

    @classmethod
    async def aclose(cls):
        pass

# Instance for compatibility if needed, though class methods are used
memory_cache = MemoryCache()
