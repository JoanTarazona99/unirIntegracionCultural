"""
Cache Service: wrapper around LRUCache.

Manages distributed caching with TTL support and structured logging.
Does not modify the underlying LRUCache implementation.
"""

from typing import Any, Dict, Optional

from app.config.logging_config import get_logger
from app.domain.exceptions import ValidationError, AppError

logger = get_logger(__name__)


class CacheService:
    """Service for cache operations.
    
    Wraps LRUCache without modifying it.
    Provides clean interface for routers with structured logging.
    Handles TTL-based expiration and LRU eviction.
    """
    
    def __init__(self, cache):
        """Initialize with LRUCache instance.
        
        Args:
            cache: LRUCache instance from main.py
            
        Raises:
            ValidationError: If cache is not initialized
        """
        if cache is None:
            raise ValidationError(
                "Cache not initialized",
                field="cache",
                context={"reason": "cache is None"}
            )
        
        self.cache = cache
        logger.info(
            "cache_service_initialized",
            module_type=type(cache).__name__,
            max_entries=cache.max_entries,
            default_ttl=cache.default_ttl
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
            
        Raises:
            ValidationError: If key is invalid
        """
        if not key or not isinstance(key, str):
            raise ValidationError(
                "Invalid cache key",
                field="key",
                context={"received": key}
            )
        
        try:
            logger.info(
                "cache_get_start",
                key=key,
                key_length=len(key)
            )
            
            value = self.cache.get(key)
            
            if value is not None:
                logger.info(
                    "cache_get_success",
                    key=key,
                    hit=True
                )
            else:
                logger.info(
                    "cache_get_miss",
                    key=key,
                    hit=False
                )
            
            return value
            
        except Exception as e:
            logger.error(
                "cache_get_failed",
                key=key,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Cache get failed: {str(e)}",
                context={"key": key},
                original_exception=e
            )
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ) -> Dict:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (any JSON-serializable type)
            ttl: Optional TTL in seconds (uses default if None)
            
        Returns:
            Dict with {success: bool, key: str, ttl: float}
            
        Raises:
            ValidationError: If key is invalid
        """
        if not key or not isinstance(key, str):
            raise ValidationError(
                "Invalid cache key",
                field="key",
                context={"received": key}
            )
        
        if ttl is not None and (not isinstance(ttl, (int, float)) or ttl < 0):
            raise ValidationError(
                "Invalid TTL",
                field="ttl",
                context={"received": ttl, "must_be": "positive number"}
            )
        
        try:
            logger.info(
                "cache_set_start",
                key=key,
                key_length=len(key),
                value_type=type(value).__name__,
                ttl=ttl or self.cache.default_ttl
            )
            
            self.cache.set(key, value, ttl)
            
            actual_ttl = ttl or self.cache.default_ttl
            
            logger.info(
                "cache_set_success",
                key=key,
                ttl=actual_ttl
            )
            
            return {
                "success": True,
                "key": key,
                "ttl": actual_ttl
            }
            
        except Exception as e:
            logger.error(
                "cache_set_failed",
                key=key,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Cache set failed: {str(e)}",
                context={"key": key},
                original_exception=e
            )
    
    def invalidate(self, key: str) -> Dict:
        """Invalidate/remove specific cache entry.
        
        Args:
            key: Cache key to remove
            
        Returns:
            Dict with {success: bool, key: str, existed: bool}
            
        Raises:
            ValidationError: If key is invalid
        """
        if not key or not isinstance(key, str):
            raise ValidationError(
                "Invalid cache key",
                field="key",
                context={"received": key}
            )
        
        try:
            logger.info(
                "cache_invalidate_start",
                key=key
            )
            
            existed = self.cache.invalidate(key)
            
            logger.info(
                "cache_invalidate_success",
                key=key,
                existed=existed
            )
            
            return {
                "success": True,
                "key": key,
                "existed": existed
            }
            
        except Exception as e:
            logger.error(
                "cache_invalidate_failed",
                key=key,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Cache invalidate failed: {str(e)}",
                context={"key": key},
                original_exception=e
            )
    
    def clear(self) -> Dict:
        """Clear all cache entries.
        
        Returns:
            Dict with {success: bool, cleared_count: int}
        """
        try:
            logger.info("cache_clear_start")
            
            count = self.cache.clear()
            
            logger.info(
                "cache_clear_success",
                cleared_count=count
            )
            
            return {
                "success": True,
                "cleared_count": count
            }
            
        except Exception as e:
            logger.error(
                "cache_clear_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Cache clear failed: {str(e)}",
                original_exception=e
            )
    
    def get_stats(self) -> Dict:
        """Get cache statistics.
        
        Returns:
            Dict with {hits, misses, evictions, expirations, size}
        """
        try:
            logger.info("cache_stats_requested")
            
            stats = self.cache.get_stats() if hasattr(self.cache, 'get_stats') else {}
            
            stats.update({
                "current_size": len(self.cache._cache),
                "max_entries": self.cache.max_entries,
                "default_ttl": self.cache.default_ttl
            })
            
            logger.info(
                "cache_stats_retrieved",
                current_size=stats.get('current_size'),
                hits=stats.get('_hits', 0),
                misses=stats.get('_misses', 0)
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                "cache_stats_failed",
                error=str(e)
            )
            return {}
    
    def get_status(self) -> Dict:
        """Get service status.
        
        Returns:
            Dict with {available: bool, size: int, max_entries: int}
        """
        try:
            logger.info("cache_status_check")
            
            current_size = len(self.cache._cache)
            
            logger.info(
                "cache_status_retrieved",
                current_size=current_size
            )
            
            return {
                "available": True,
                "size": current_size,
                "max_entries": self.cache.max_entries,
                "default_ttl": self.cache.default_ttl
            }
            
        except Exception as e:
            logger.error(
                "cache_status_failed",
                error=str(e)
            )
            return {
                "available": False,
                "error": str(e)
            }
