"""
Cache Module - LRU Cache with TTL for RAG query results

Features:
- LRU eviction when max entries reached
- TTL (time-to-live) expiration
- Thread-safe operations
- Cache statistics tracking
"""

import time
import hashlib
from typing import Any, Optional, Dict, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import threading


@dataclass
class CacheEntry:
    """Single cache entry with value and expiration"""
    value: Any
    created_at: float
    ttl_seconds: float
    access_count: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() > (self.created_at + self.ttl_seconds)

    def touch(self):
        """Mark entry as accessed"""
        self.access_count += 1


class LRUCache:
    """
    LRU Cache with TTL support

    Thread-safe cache that evicts:
    - Expired entries (TTL-based)
    - Least recently used entries (when max size reached)

    Usage:
        cache = LRUCache(max_entries=500, default_ttl=3600)
        cache.set("key", {"data": "value"})
        result = cache.get("key")
    """

    def __init__(self, max_entries: int = 500, default_ttl: float = 3600):
        """
        Initialize LRU cache

        Args:
            max_entries: Maximum number of entries (default 500)
            default_ttl: Default TTL in seconds (default 1 hour = 3600)
        """
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        Generate cache key from arguments

        Usage:
            key = LRUCache.generate_key(query, user_language)
        """
        key_data = {"args": args, "kwargs": kwargs}
        key_string = str(key_data)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check TTL expiration
            if entry.is_expired():
                del self._cache[key]
                self._expirations += 1
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1

            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (uses default if not provided)
        """
        with self._lock:
            # Remove expired entries first
            self._cleanup_expired()

            # Evict LRU if at capacity
            while len(self._cache) >= self.max_entries:
                self._cache.popitem(last=False)  # Remove oldest (LRU)
                self._evictions += 1

            # If key exists, remove it (will be re-added at end)
            if key in self._cache:
                del self._cache[key]

            # Add new entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl or self.default_ttl
            )
            self._cache[key] = entry

    def invalidate(self, key: str) -> bool:
        """
        Invalidate/remove specific cache entry

        Args:
            key: Cache key to remove

        Returns:
            True if entry existed and was removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """
        Clear all cache entries

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def _cleanup_expired(self) -> int:
        """
        Remove all expired entries

        Returns:
            Number of entries removed
        """
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]
            self._expirations += 1

        return len(expired_keys)

    def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: Optional[float] = None
    ) -> Any:
        """
        Get from cache, or compute and cache if missing

        Args:
            key: Cache key
            factory: Function to compute value if not cached
            ttl: Optional TTL override

        Returns:
            Cached or computed value
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        # Compute new value
        value = factory()
        self.set(key, value, ttl)
        return value

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "entries": len(self._cache),
                "max_entries": self.max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self._evictions,
                "expirations": self._expirations,
                "total_requests": total_requests,
                "ttl_seconds": self.default_ttl
            }

    def get_keys(self) -> list:
        """Get all cache keys"""
        with self._lock:
            return list(self._cache.keys())


# Global cache instance for RAG queries
_rag_cache: Optional[LRUCache] = None


def get_rag_cache(max_entries: int = 500, default_ttl: float = 3600) -> LRUCache:
    """
    Get or create global RAG cache instance

    Default TTL: 1 hour (3600 seconds)
    Max entries: 500
    """
    global _rag_cache
    if _rag_cache is None:
        _rag_cache = LRUCache(max_entries=max_entries, default_ttl=default_ttl)
    return _rag_cache


def cache_rag_query(query: str, language: str, result: Dict) -> None:
    """
    Cache RAG query result

    Key is generated from query + language
    """
    cache = get_rag_cache()
    key = LRUCache.generate_key(query, language)
    cache.set(key, result)


def get_cached_rag_query(query: str, language: str) -> Optional[Dict]:
    """
    Get cached RAG query result

    Returns None if not cached or expired
    """
    cache = get_rag_cache()
    key = LRUCache.generate_key(query, language)
    return cache.get(key)


if __name__ == "__main__":
    # Test the cache
    cache = LRUCache(max_entries=5, default_ttl=10)

    print("Testing LRU Cache...")
    print("-" * 40)

    # Test basic set/get
    cache.set("key1", {"data": "value1"})
    cache.set("key2", {"data": "value2"})

    print(f"Get key1: {cache.get('key1')}")
    print(f"Get key2: {cache.get('key2')}")
    print(f"Get nonexistent: {cache.get('key3')}")

    # Test LRU eviction
    for i in range(10):
        cache.set(f"item_{i}", f"value_{i}")

    print(f"\nAfter adding 10 items to cache of size 5:")
    print(f"Cache size: {len(cache.get_keys())}")
    print(f"Keys: {cache.get_keys()}")

    # Test stats
    print(f"\nCache stats: {cache.get_stats()}")

    # Test TTL
    import time
    small_cache = LRUCache(max_entries=5, default_ttl=1)  # 1 second TTL
    small_cache.set("ttl_test", "will_expire")
    print(f"\nWith 1s TTL:")
    print(f"Immediate get: {small_cache.get('ttl_test')}")
    time.sleep(2)
    print(f"After 2s: {small_cache.get('ttl_test')} (expired)")
