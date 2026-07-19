from abc import ABC, abstractmethod
from hashlib import md5
from core.logger import logger

class BaseCache(ABC):
    @abstractmethod
    def get(self, query: str):
        pass

    @abstractmethod
    def set(self, query: str, answer: str):
        pass

    @abstractmethod
    def clear(self):
        pass

class MemoryCache(BaseCache):
    def __init__(self, max_size: int = 1000):
        self._store = {}
        self.max_size = max_size

    def get(self, query: str):
        key = md5(query.encode("utf-8")).hexdigest()
        return self._store.get(key)

    def set(self, query: str, answer: str):
        if len(self._store) >= self.max_size:
            half = self.max_size // 2
            keys = list(self._store.keys())
            for k in keys[:half]:
                del self._store[k]
            logger.info("cache_eviction", removed=half)
        key = md5(query.encode("utf-8")).hexdigest()
        self._store[key] = answer

    def clear(self):
        self._store.clear()
        logger.info("cache_cleared")

class RedisCache(BaseCache):
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._fallback = MemoryCache()
        logger.warning("RedisCache not implemented, falling back to MemoryCache")

    def get(self, query: str):
        return self._fallback.get(query)

    def set(self, query: str, answer: str):
        self._fallback.set(query, answer)

    def clear(self):
        self._fallback.clear()