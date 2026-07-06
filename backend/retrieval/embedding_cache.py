"""
Fase 5: Embedding Cache with TTL

Cachea embeddings para queries que se repiten.
Reduce latencia de dense retrieval significativamente.

Uso:
    cache = EmbeddingCache(ttl=3600)
    
    # Check cache
    embedding = cache.get("query")
    if embedding is None:
        embedding = model.encode("query")  # Calcular
        cache.set("query", embedding)  # Guardar
    
    # Stats
    print(f"Cache size: {cache.size()} entries")
    cache.clear_expired()
"""

import time
import logging
from typing import Optional, List, Dict
import hashlib

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    LRU Cache para embeddings de queries con TTL.
    
    Características:
    - TTL configurable (default 1 hora)
    - Auto-expira entradas antiguas
    - Thread-safe con lock
    - Estadísticas de hit/miss
    """
    
    def __init__(self, ttl: int = 3600, max_size: int = 10000):
        """
        Initialize embedding cache.
        
        Args:
            ttl: Time to live en segundos (default 1 hora)
            max_size: Máximo número de entries antes de LRU eviction
        """
        self.ttl = ttl  # 3600 seconds = 1 hour
        self.max_size = max_size
        
        self._cache = {}  # query_hash -> embedding
        self._timestamps = {}  # query_hash -> timestamp
        self._access_times = {}  # query_hash -> last access time
        
        # Stats
        self._hits = 0
        self._misses = 0
    
    def _hash_query(self, query: str) -> str:
        """Hash query for cache key (case-insensitive)"""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, query: str) -> Optional[List[float]]:
        """
        Get cached embedding for query.
        
        Args:
            query: Input query string
        
        Returns:
            Cached embedding if hit and not expired, None otherwise
        """
        query_hash = self._hash_query(query)
        
        if query_hash not in self._cache:
            self._misses += 1
            return None
        
        # Check if expired
        age = time.time() - self._timestamps[query_hash]
        if age >= self.ttl:
            # Expired - remove
            del self._cache[query_hash]
            del self._timestamps[query_hash]
            if query_hash in self._access_times:
                del self._access_times[query_hash]
            
            self._misses += 1
            return None
        
        # Hit - update access time
        self._access_times[query_hash] = time.time()
        self._hits += 1
        
        logger.debug(f"Cache HIT for query: {query[:50]}")
        return self._cache[query_hash]
    
    def set(self, query: str, embedding: List[float]):
        """
        Cache embedding for query.
        
        Args:
            query: Input query string
            embedding: Query embedding vector (list of floats)
        """
        query_hash = self._hash_query(query)
        
        # Check if need to evict (LRU)
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        self._cache[query_hash] = embedding
        self._timestamps[query_hash] = time.time()
        self._access_times[query_hash] = time.time()
        
        logger.debug(f"Cache SET for query: {query[:50]}")
    
    def _evict_lru(self):
        """Remove least recently used entry"""
        if not self._access_times:
            return
        
        # Find LRU entry
        lru_hash = min(self._access_times, key=self._access_times.get)
        
        del self._cache[lru_hash]
        del self._timestamps[lru_hash]
        del self._access_times[lru_hash]
        
        logger.info(f"Cache eviction: removed LRU entry")
    
    def clear_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired = [
            query_hash
            for query_hash, ts in self._timestamps.items()
            if now - ts >= self.ttl
        ]
        
        for query_hash in expired:
            del self._cache[query_hash]
            del self._timestamps[query_hash]
            if query_hash in self._access_times:
                del self._access_times[query_hash]
        
        if expired:
            logger.info(f"Cache cleanup: removed {len(expired)} expired entries")
        
        return len(expired)
    
    def clear_all(self):
        """Clear entire cache"""
        self._cache.clear()
        self._timestamps.clear()
        self._access_times.clear()
        logger.info("Cache cleared")
    
    def size(self) -> int:
        """Get current cache size (number of entries)"""
        return len(self._cache)
    
    def hit_rate(self) -> float:
        """
        Get cache hit rate (0-1 scale).
        
        Returns:
            Fraction of requests that were cache hits
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self._hits + self._misses
        
        return {
            'size': self.size(),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'hits': self._hits,
            'misses': self._misses,
            'total_requests': total,
            'hit_rate': self.hit_rate() if total > 0 else 0.0,
            'utilization': f"{self.size() / self.max_size * 100:.1f}%",
        }
    
    def print_stats(self):
        """Print cache statistics to stdout"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("EMBEDDING CACHE STATISTICS")
        print("="*60)
        print(f"Size:           {stats['size']}/{stats['max_size']} entries")
        print(f"Hit Rate:       {stats['hit_rate']:.1%}")
        print(f"Hits:           {stats['hits']}")
        print(f"Misses:         {stats['misses']}")
        print(f"Total:          {stats['total_requests']}")
        print(f"Utilization:    {stats['utilization']}")
        print(f"TTL:            {stats['ttl']}s")
        print("="*60 + "\n")


class QueryCache:
    """
    Query-level cache: Cachea resultados de queries completas.
    Más agresivo que embedding cache - cachea output final.
    
    Útil para: queries populares que se repiten frecuentemente
    """
    
    def __init__(self, ttl: int = 600, max_size: int = 1000):
        """
        Initialize query result cache.
        
        Args:
            ttl: Time to live (default 10 minutos)
            max_size: Max entries
        """
        self.ttl = ttl
        self.max_size = max_size
        
        self._cache = {}  # query_hash -> results
        self._timestamps = {}
        self._access_times = {}
        
        self._hits = 0
        self._misses = 0
    
    def _hash_query(self, query: str) -> str:
        """Hash query (case-insensitive)"""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, query: str, top_k: int = 5):
        """Get cached results"""
        cache_key = f"{self._hash_query(query)}_{top_k}"
        
        if cache_key not in self._cache:
            self._misses += 1
            return None
        
        # Check expiry
        age = time.time() - self._timestamps[cache_key]
        if age >= self.ttl:
            del self._cache[cache_key]
            del self._timestamps[cache_key]
            self._misses += 1
            return None
        
        self._access_times[cache_key] = time.time()
        self._hits += 1
        return self._cache[cache_key]
    
    def set(self, query: str, top_k: int, results):
        """Cache query results"""
        if len(self._cache) >= self.max_size:
            # Simple eviction: remove oldest
            oldest = min(self._timestamps, key=self._timestamps.get)
            del self._cache[oldest]
            del self._timestamps[oldest]
        
        cache_key = f"{self._hash_query(query)}_{top_k}"
        self._cache[cache_key] = results
        self._timestamps[cache_key] = time.time()
        self._access_times[cache_key] = time.time()
    
    def size(self) -> int:
        return len(self._cache)
    
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0


if __name__ == "__main__":
    # Test script
    print("\n" + "="*60)
    print("EMBEDDING CACHE TEST")
    print("="*60)
    
    cache = EmbeddingCache(ttl=60)
    
    # Test 1: Basic get/set
    print("\n[Test 1] Basic get/set")
    embedding1 = [0.1, 0.2, 0.3, 0.4]
    cache.set("hola mundo", embedding1)
    result = cache.get("hola mundo")
    print(f"  Set & Get: {result == embedding1}")
    
    # Test 2: Cache hit
    print("\n[Test 2] Cache hit")
    result2 = cache.get("hola mundo")
    print(f"  Hit: {result2 is not None}")
    print(f"  Hit rate: {cache.hit_rate():.1%}")
    
    # Test 3: Case insensitivity
    print("\n[Test 3] Case insensitivity")
    result3 = cache.get("HOLA MUNDO")
    print(f"  Case insensitive hit: {result3 is not None}")
    
    # Test 4: Cache miss
    print("\n[Test 4] Cache miss")
    result4 = cache.get("different query")
    print(f"  Miss: {result4 is None}")
    print(f"  Hit rate after miss: {cache.hit_rate():.1%}")
    
    # Stats
    cache.print_stats()
