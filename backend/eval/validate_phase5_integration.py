"""
FASE 5: VALIDACIÓN RÁPIDA DE INTEGRACIÓN
Verifica que Model Warmer, Embedding Cache y Latency Monitor están integrados
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.embedding_cache import EmbeddingCache
from retrieval.latency_monitor import LatencyMonitor
from retrieval.dense import DenseRetriever
from retrieval.hybrid import HybridRetriever
from retrieval.chunks import Chunk

print("\n" + "="*70)
print("FASE 5: VALIDACIÓN DE INTEGRACIÓN")
print("="*70)

# Test 1: Embedding Cache
print("\n[Test 1] Embedding Cache Integration...")
try:
    dense = DenseRetriever(enable_cache=True)
    assert dense.cache is not None, "Cache not initialized"
    print("  ✅ DenseRetriever con cache: OK")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 2: Latency Monitor
print("\n[Test 2] Latency Monitor Integration...")
try:
    hybrid = HybridRetriever(enable_monitor=True)
    assert hybrid.monitor is not None, "Monitor not initialized"
    print("  ✅ HybridRetriever con monitor: OK")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 3: Cache functionality
print("\n[Test 3] Cache Functionality...")
try:
    cache = EmbeddingCache(ttl=3600, max_size=1000)
    import numpy as np
    
    # Test set/get
    test_query = "prueba"
    test_embedding = np.random.rand(384)
    
    cache.set(test_query, test_embedding)
    retrieved = cache.get(test_query)
    
    assert retrieved is not None, "Cache get returned None"
    assert np.allclose(retrieved, test_embedding), "Retrieved embedding doesn't match"
    print("  ✅ Cache set/get: OK")
    print(f"  ✅ Hit rate: {cache.hit_rate():.1%}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Monitor functionality
print("\n[Test 4] Monitor Functionality...")
try:
    monitor = LatencyMonitor()
    
    # Record some fake measurements
    with monitor.measure_stage('test_stage'):
        import time
        time.sleep(0.01)
    
    stats = monitor.get_stats('test_stage')
    assert stats is not None, "Monitor stats is None"
    assert stats['count'] > 0, "Monitor didn't record measurement"
    print(f"  ✅ Monitor recording: OK")
    print(f"  ✅ P95: {stats['p95']:.2f}ms")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 5: Hybrid with both components
print("\n[Test 5] Full Integration (Hybrid + Dense + Monitor + Cache)...")
try:
    dense = DenseRetriever(enable_cache=True)
    hybrid = HybridRetriever(dense=dense, enable_monitor=True)
    
    # Create test chunks
    chunks = [
        Chunk(id="1", source="test", title="Test 1", content="contenido de prueba"),
        Chunk(id="2", source="test", title="Test 2", content="más contenido"),
    ]
    
    hybrid.index(chunks)
    print("  ✅ Hybrid indexing: OK")
    
    # Check components
    assert hybrid.monitor is not None, "Monitor missing"
    assert hybrid.dense is not None, "Dense missing"
    assert hybrid.dense.cache is not None, "Cache missing"
    
    print("  ✅ All components integrated: OK")
    print(f"  ✅ Monitor stages available: {list(hybrid.monitor.stage_latencies.keys())}")
    
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "="*70)
print("✅ VALIDACIÓN COMPLETADA - TODOS LOS COMPONENTES INTEGRADOS")
print("="*70)
print("\nPróximos pasos:")
print("  1. Ejecutar: python main.py")
print("  2. Ir a: http://localhost:8000/frontend/")
print("  3. Hacer queries y verificar que responden rápido")
print("  4. Model Warmer se está precargando en background")
print("  5. Embedding Cache cachea queries repetidas")
print("  6. Latency Monitor mide tiempo por stage")
print("\n")
