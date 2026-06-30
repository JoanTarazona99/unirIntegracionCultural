"""
Redis-backed cache service with LRU fallback.

Implements same interface as CacheService but uses Redis as backend.
If Redis is unavailable, automatically falls back to in-memory LRU cache.
"""

from typing import Any, Dict, Optional
from app.config.logging_config import get_logger
from app.domain.exceptions import ValidationError, AppError
from app.services.cache_service import CacheService  # For fallback

logger = get_logger(__name__)


class RedisCacheService:
    """
    Redis cache service with automatic fallback to LRU cache.
    
    Uses redis.asyncio (aioredis) for async operations.
    Gracefully falls back to in-memory LRU if Redis unavailable.
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize Redis cache service.
        
        Args:
            redis_client: Optional redis.asyncio.Redis client
                         If None, will use fallback LRU cache
        """
        self.redis_client = redis_client
        self.fallback_cache = None
        self.using_redis = redis_client is not None
        
        if not self.using_redis:
            # Initialize fallback LRU cache
            from cache_module import get_rag_cache
            self.fallback_cache = get_rag_cache(max_entries=500, default_ttl=3600)
            logger.info(
                "redis_cache_initialized_fallback",
                backend="lru",
                reason="Redis client not provided"
            )
        else:
            logger.info(
                "redis_cache_initialized",
                backend="redis",
                redis_url="redis://localhost:6379"
            )
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not key or not isinstance(key, str):
            raise ValidationError("Cache key must be non-empty string", field="key")
        
        logger.info("cache_get_start", key=key, key_length=len(key))
        
        try:
            if self.using_redis:
                # Try Redis
                import redis
                try:
                    value = await self.redis_client.get(key)
                    if value is not None:
                        logger.info("cache_get_success", key=key, hit=True, source="redis")
                        # Redis returns bytes, decode if needed
                        if isinstance(value, bytes):
                            import json
                            return json.loads(value.decode('utf-8'))
                        return value
                    else:
                        logger.info("cache_get_miss", key=key, source="redis")
                        return None
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    # Redis failed, switch to fallback
                    logger.warning(
                        "redis_get_failed_switching_fallback",
                        key=key,
                        error=str(e)
                    )
                    self.using_redis = False
                    self.fallback_cache = __import__('cache_module').get_rag_cache()
                    return self.fallback_cache.get(key)
            
            # Use fallback LRU
            value = self.fallback_cache.get(key)
            if value is not None:
                logger.info("cache_get_success", key=key, hit=True, source="lru")
            else:
                logger.info("cache_get_miss", key=key, source="lru")
            return value
            
        except Exception as e:
            logger.error("cache_get_failed", key=key, error=str(e))
            raise AppError(f"Cache get failed: {str(e)}", context={"key": key})
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """
        Set cache value with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        if not key or not isinstance(key, str):
            raise ValidationError("Cache key must be non-empty string", field="key")
        if ttl < 0:
            raise ValidationError("TTL must be non-negative", field="ttl")
        
        logger.info(
            "cache_set_start",
            key=key,
            key_length=len(key),
            value_type=type(value).__name__,
            ttl=ttl
        )
        
        try:
            if self.using_redis:
                # Try Redis
                import redis
                import json
                try:
                    # Serialize value for Redis
                    serialized = json.dumps(value) if not isinstance(value, str) else value
                    await self.redis_client.setex(
                        key,
                        ttl,
                        serialized
                    )
                    logger.info("cache_set_success", key=key, ttl=ttl, source="redis")
                    return True
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    # Redis failed, switch to fallback
                    logger.warning(
                        "redis_set_failed_switching_fallback",
                        key=key,
                        error=str(e)
                    )
                    self.using_redis = False
                    self.fallback_cache = __import__('cache_module').get_rag_cache()
                    self.fallback_cache.set(key, value, ttl=ttl)
                    return True
            
            # Use fallback LRU
            self.fallback_cache.set(key, value, ttl=ttl)
            logger.info("cache_set_success", key=key, ttl=ttl, source="lru")
            return True
            
        except Exception as e:
            logger.error("cache_set_failed", key=key, error=str(e))
            raise AppError(f"Cache set failed: {str(e)}", context={"key": key})
    
    async def invalidate(self, key: str) -> bool:
        """
        Invalidate cache key.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if successful
        """
        if not key or not isinstance(key, str):
            raise ValidationError("Cache key must be non-empty string", field="key")
        
        logger.info("cache_invalidate_start", key=key, key_length=len(key))
        
        try:
            if self.using_redis:
                import redis
                try:
                    await self.redis_client.delete(key)
                    logger.info("cache_invalidate_success", key=key, source="redis")
                    return True
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    logger.warning("redis_invalidate_failed_using_fallback", error=str(e))
                    self.using_redis = False
                    self.fallback_cache = __import__('cache_module').get_rag_cache()
                    self.fallback_cache.invalidate(key)
                    return True
            
            # Use fallback LRU
            self.fallback_cache.invalidate(key)
            logger.info("cache_invalidate_success", key=key, source="lru")
            return True
            
        except Exception as e:
            logger.error("cache_invalidate_failed", key=key, error=str(e))
            raise AppError(f"Cache invalidate failed: {str(e)}", context={"key": key})
    
    async def clear(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        logger.info("cache_clear_start")
        
        try:
            if self.using_redis:
                import redis
                try:
                    await self.redis_client.flushdb()
                    logger.info("cache_clear_success", source="redis")
                    return 0  # Redis doesn't tell us count
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    logger.warning("redis_clear_failed_using_fallback", error=str(e))
                    self.using_redis = False
                    self.fallback_cache = __import__('cache_module').get_rag_cache()
                    return self.fallback_cache.clear()
            
            # Use fallback LRU
            cleared = self.fallback_cache.clear()
            logger.info("cache_clear_success", cleared_count=cleared, source="lru")
            return cleared
            
        except Exception as e:
            logger.error("cache_clear_failed", error=str(e))
            raise AppError(f"Cache clear failed: {str(e)}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with stats (implementation-dependent)
        """
        logger.info("cache_stats_requested")
        
        try:
            if self.using_redis:
                import redis
                try:
                    info = await self.redis_client.info()
                    stats = {
                        "used_memory": info.get("used_memory", 0),
                        "connected_clients": info.get("connected_clients", 0),
                        "total_commands_processed": info.get("total_commands_processed", 0),
                    }
                    logger.info("cache_stats_retrieved", backend="redis", stats=stats)
                    return stats
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    logger.warning("redis_stats_failed_using_fallback", error=str(e))
                    self.using_redis = False
                    self.fallback_cache = __import__('cache_module').get_rag_cache()
                    return self.fallback_cache.get_stats()
            
            # Use fallback LRU
            stats = self.fallback_cache.get_stats()
            logger.info("cache_stats_retrieved", backend="lru", stats=stats)
            return stats
            
        except Exception as e:
            logger.error("cache_stats_failed", error=str(e))
            raise AppError(f"Cache stats failed: {str(e)}")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get cache service status.
        
        Returns:
            Dict with status info including backend type
        """
        logger.info("cache_status_check")
        
        try:
            if self.using_redis:
                import redis
                try:
                    ping = await self.redis_client.ping()
                    status = {
                        "available": ping,
                        "backend_type": "redis",
                        "connection_url": "redis://localhost:6379",
                    }
                    logger.info("cache_status_retrieved", backend="redis", available=ping)
                    return status
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    logger.warning("redis_status_check_failed", error=str(e))
                    self.using_redis = False
                    self.fallback_cache = __import__('cache_module').get_rag_cache()
                    return {
                        "available": True,
                        "backend_type": "lru",
                        "fallback_reason": "redis_unavailable",
                    }
            
            # Use fallback LRU
            status = {
                "available": True,
                "backend_type": "lru",
                "fallback_reason": "redis_not_enabled" if not self.redis_client else "redis_connection_failed",
            }
            logger.info("cache_status_retrieved", backend="lru", available=True)
            return status
            
        except Exception as e:
            logger.error("cache_status_failed", error=str(e))
            raise AppError(f"Cache status failed: {str(e)}")
