import json
import logging
from typing import Any, Optional

import redis

from config import settings

logger = logging.getLogger(__name__)


class CacheClient:
    def __init__(self):
        try:
            self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.client.ping()
            self._available = True
            logger.info("Redis connected successfully")
        except Exception as e:
            self._available = False
            logger.warning(f"Redis unavailable: {e}. Caching disabled.")

    def get(self, key: str) -> Optional[Any]:
        """Get value. Returns None if key missing or Redis down."""
        if not self._available:
            return None
        try:
            value = self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value with TTL in seconds. Returns False if Redis down."""
        if not self._available:
            return False
        try:
            self.client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        if not self._available:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern. Returns count deleted."""
        if not self._available:
            return 0
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete_pattern error for {pattern}: {e}")
            return 0

    def increment(self, key: str, ttl: int = 60) -> int:
        """Increment counter. Used for rate limiting."""
        if not self._available:
            return 0
        try:
            pipe = self.client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)
            results = pipe.execute()
            return results[0]
        except Exception as e:
            logger.warning(f"Cache increment error for {key}: {e}")
            return 0

    def exists(self, key: str) -> bool:
        if not self._available:
            return False
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists error for {key}: {e}")
            return False

    def set_with_nx(self, key: str, value: Any, ttl: int) -> bool:
        """Set only if not exists (for cache locks). Returns True if set."""
        if not self._available:
            return True  # Allow operation if Redis down
        try:
            result = self.client.set(key, json.dumps(value, default=str), nx=True, ex=ttl)
            return result is not None
        except Exception as e:
            logger.warning(f"Cache setnx error for {key}: {e}")
            return True

    def ttl(self, key: str) -> int:
        """Return remaining TTL in seconds. -1 if no expiry, -2 if key missing."""
        if not self._available:
            return -2
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.warning(f"Cache ttl error for {key}: {e}")
            return -2


class CacheKeys:
    USER = "user:{user_id}"
    MEMBER_LIST = "members:user:{user_id}"
    MEMBER = "member:{member_id}"
    PROGRAM = "program:{program_id}"
    ADHERENCE_DAILY = "adherence:{member_id}:{component}:{date}"
    ADHERENCE_ROLLING = "adherence:rolling:{member_id}:{component}"
    SUMMARY = "summary:{program_id}:{week_number}"
    RATE_LIMIT = "rate:{endpoint}:{ip}:{minute}"
    TOKEN_BLACKLIST = "blacklist:token:{jti}"

    @staticmethod
    def format(template: str, **kwargs) -> str:
        return template.format(**kwargs)


# Singleton — imported by all modules
cache = CacheClient()
