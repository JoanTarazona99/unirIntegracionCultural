"""
INTEGRACIÓN DE HYBRID_RAG EN ENHANCED_RAG.PY

Archivo de referencia: Cómo integrar HybridRAGEngine en el pipeline actual.

UBICACIÓN ACTUAL EN enhanced_rag.py:
  - Línea ~1039: OfficialDocumentLibrary.search()
  - Línea ~1230: citation_guard activado
  - Línea ~1302: search_and_generate()
  - Línea ~1362: enforce_grounding_improved()
"""

# ==============================================================================
# OPCIÓN A: REEMPLAZAR search() en OfficialDocumentLibrary (Simple)
# ==============================================================================

# ANTES (línea ~1039):
"""
def search(self, query: str, source: Optional[str] = None) -> List[Dict]:
    # Try semantic search first
    if self._use_semantic and self.semantic_engine:
        semantic_results = self.semantic_engine.search(query, top_k=5)
        if semantic_results:
            results = []
            for doc, similarity in semantic_results:
                results.append({
                    'source': doc['source'],
                    'source_url': doc['source_url'],
                    'title': doc['title'],
                    'content': doc['content'],
                    'relevance': similarity,
                    'search_mode': 'semantic'
                })
            return results
    
    # Fallback to keyword search
    return self._keyword_search(query, source)
"""

# DESPUÉS (Opción A - Simple):
"""
def search(self, query: str, source: Optional[str] = None) -> List[Dict]:
    '''Search using Hybrid Retriever (BM25 + Dense + Rerank)'''
    
    # Initialize hybrid engine once
    if not hasattr(self, '_hybrid_engine'):
        from hybrid_rag import HybridRAGEngine
        
        self._hybrid_engine = HybridRAGEngine(
            enable_dense=getattr(self.config, 'enable_hybrid_dense', True),
            enable_reranking=getattr(self.config, 'enable_hybrid_reranking', True),
            top_k=5,
        )
        
        # Index all documents
        chunks = self._documents_to_chunks()
        self._hybrid_engine.index(chunks)
    
    # Search using hybrid engine
    try:
        hybrid_results = self._hybrid_engine.search(query, top_k=5)
        
        # Format results to match existing API
        results = []
        for result in hybrid_results:
            results.append({
                'source': result['source'],
                'source_url': self._get_source_url(result['source']),
                'title': result['title'],
                'content': result['content'],
                'relevance': result['score'],
                'search_mode': 'hybrid',
                'language_detected': result['language_detected'],
            })
        return results
    
    except Exception as e:
        logger.warning(f"Hybrid search failed, fallback to BM25: {e}")
        return self._keyword_search(query, source)

def _documents_to_chunks(self) -> List[Chunk]:
    '''Convert internal documents to Chunk format for HybridRAGEngine'''
    from retrieval.chunks import Chunk
    
    chunks = []
    for doc in self.documents:
        chunk = Chunk(
            id=doc.get('id', doc.get('title', 'unknown')),
            source=doc.get('source', 'Unknown'),
            title=doc.get('title', ''),
            content=doc.get('content', ''),
        )
        chunks.append(chunk)
    return chunks

def _get_source_url(self, source: str) -> str:
    '''Get URL for source'''
    urls = {
        'KubGU': 'https://kubsu.ru',
        'MVD': 'https://mvd.gov.ru',
        'MFC': 'https://mfc.gov.ru',
        'Gosuslugi': 'https://gosuslugi.ru',
    }
    return urls.get(source, '')
"""

# ==============================================================================
# OPCIÓN B: CREAR HYBRID ENGINE COMO COMPONENTE SEPARADO (Production)
# ==============================================================================

"""
UBICACIÓN: backend/app/services/retrieval_service.py (NUEVO)

from hybrid_rag import HybridRAGEngine, HybridRAGConfig
from retrieval.chunks import Chunk
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class RetrievalService:
    '''Unified retrieval service supporting BM25 and Hybrid modes'''
    
    def __init__(self, mode: str = 'hybrid'):
        self.mode = mode  # 'bm25', 'hybrid', 'auto'
        self.config = HybridRAGConfig()
        self._engine = None
        self._initialized = False
    
    def initialize(self, documents: List[Dict]):
        '''Initialize retrieval engine with documents'''
        
        if self.mode == 'hybrid':
            self._engine = HybridRAGEngine(
                enable_dense=self.config.ENABLE_DENSE,
                enable_reranking=self.config.ENABLE_RERANKING,
                top_k=self.config.TOP_K,
            )
        else:
            # TODO: Implement BM25-only fallback
            raise NotImplementedError(f"Mode {self.mode} not implemented")
        
        # Convert documents to chunks
        chunks = self._to_chunks(documents)
        self._engine.index(chunks)
        self._initialized = True
        logger.info(f"RetrievalService initialized with {len(chunks)} chunks")
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        '''Search for relevant documents'''
        
        if not self._initialized:
            raise RuntimeError("RetrievalService not initialized. Call initialize() first.")
        
        try:
            return self._engine.search(query, top_k=top_k or 5)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _to_chunks(self, documents: List[Dict]) -> List[Chunk]:
        '''Convert documents to Chunk format'''
        chunks = []
        for doc in documents:
            chunk = Chunk(
                id=doc.get('id', doc.get('title', 'unknown')),
                source=doc.get('source', 'Unknown'),
                title=doc.get('title', ''),
                content=doc.get('content', ''),
            )
            chunks.append(chunk)
        return chunks
    
    def get_stats(self) -> Dict:
        '''Get engine statistics'''
        if self._engine:
            return self._engine.get_stats()
        return {}


# THEN IN enhanced_rag.py:
class OfficialDocumentLibrary:
    def __init__(self, ...):
        ...
        # Initialize retrieval service
        self.retrieval_service = RetrievalService(mode='hybrid')
    
    def initialize(self):
        '''Initialize library after loading documents'''
        self.retrieval_service.initialize(self.documents)
    
    def search(self, query: str, source: Optional[str] = None) -> List[Dict]:
        '''Hybrid search'''
        results = self.retrieval_service.search(query, top_k=5)
        
        # Filter by source if requested
        if source:
            results = [r for r in results if r['source'] == source]
        
        return results
"""

# ==============================================================================
# OPCIÓN C: CONFIGURACIÓN VÍA VARIABLES DE ENTORNO (Recomendado)
# ==============================================================================

"""
.env FILE:
═══════════════════════════════════════════════════════════════════════════════

# Hybrid Retrieval Configuration
ENABLE_HYBRID_RETRIEVAL=1
ENABLE_HYBRID_DENSE=1
ENABLE_HYBRID_RERANKING=1
HYBRID_TOP_K=5
HYBRID_CANDIDATE_MULTIPLIER=4

# Score Fusion Weights (BM25, Dense, Rerank)
HYBRID_FUSION_WEIGHT_BM25=0.3
HYBRID_FUSION_WEIGHT_DENSE=0.4
HYBRID_FUSION_WEIGHT_RERANK=0.3

# Or use preset: normal, bm25_heavy, dense_heavy
HYBRID_FUSION_PRESET=normal

# Caching (for Phase 5)
ENABLE_EMBEDDING_CACHE=1
EMBEDDING_CACHE_TTL=3600


EN CÓDIGO (app/config/settings.py):
─────────────────────────────────────────────────────────────────────────────

import os
from hybrid_rag import HybridRAGConfig

class Settings:
    # Hybrid Retrieval
    ENABLE_HYBRID_RETRIEVAL = os.getenv("ENABLE_HYBRID_RETRIEVAL", "1") == "1"
    ENABLE_HYBRID_DENSE = os.getenv("ENABLE_HYBRID_DENSE", "1") == "1"
    ENABLE_HYBRID_RERANKING = os.getenv("ENABLE_HYBRID_RERANKING", "1") == "1"
    HYBRID_TOP_K = int(os.getenv("HYBRID_TOP_K", "5"))
    HYBRID_CANDIDATE_MULTIPLIER = int(os.getenv("HYBRID_CANDIDATE_MULTIPLIER", "4"))
    
    # Fusion Weights
    HYBRID_FUSION_PRESET = os.getenv("HYBRID_FUSION_PRESET", "normal")
    
    @property
    def hybrid_fusion_weights(self):
        '''Get fusion weights from config'''
        return HybridRAGConfig.get_weights_for_query_type(self.HYBRID_FUSION_PRESET)


EN enhanced_rag.py:
─────────────────────────────────────────────────────────────────────────────

from app.config.settings import settings
from hybrid_rag import HybridRAGEngine

class OfficialDocumentLibrary:
    def __init__(self, ...):
        ...
        if settings.ENABLE_HYBRID_RETRIEVAL:
            self._init_hybrid_engine()
        else:
            self._use_semantic = False
    
    def _init_hybrid_engine(self):
        '''Initialize hybrid retrieval engine'''
        self._hybrid_engine = HybridRAGEngine(
            enable_dense=settings.ENABLE_HYBRID_DENSE,
            enable_reranking=settings.ENABLE_HYBRID_RERANKING,
            top_k=settings.HYBRID_TOP_K,
            candidate_multiplier=settings.HYBRID_CANDIDATE_MULTIPLIER,
        )
        logger.info("Hybrid retrieval engine initialized")
    
    def search(self, query: str, source: Optional[str] = None) -> List[Dict]:
        '''Search using configured retrieval method'''
        
        if hasattr(self, '_hybrid_engine'):
            return self._search_hybrid(query, source)
        else:
            return self._keyword_search(query, source)
    
    def _search_hybrid(self, query: str, source: Optional[str] = None) -> List[Dict]:
        '''Hybrid search using BM25 + Dense + Rerank'''
        
        if not hasattr(self, '_hybrid_indexed'):
            # One-time indexing
            chunks = self._documents_to_chunks()
            self._hybrid_engine.index(chunks)
            self._hybrid_indexed = True
        
        results = self._hybrid_engine.search(query, top_k=5)
        
        # Filter by source if needed
        if source:
            results = [r for r in results if r['source'] == source]
        
        return results
"""

# ==============================================================================
# INTEGRACIÓN CON CITATION GUARD (Línea ~1362)
# ==============================================================================

"""
UBICACIÓN ACTUAL:
  if self._retrieval_config.get("citation_guard") and results:
      try:
          from trust import enforce_grounding_improved
          grounding = enforce_grounding_improved(...)
      except:
          # Fallback

CAMBIO REQUERIDO:
  Ninguno - Funciona con cualquier retriever
  El citation_guard funciona con:
  - results['content'] (cualquier retriever lo proporciona)
  - results['score'] (hybrid lo proporciona en [0,1])

BENEFICIO:
  - Hybrid mejora relevancia de retrieval
  - Citation guard mejora relevancia de grounding
  - Combinación = mejor precisión general
"""

# ==============================================================================
# MIGRACIÓN PASO A PASO
# ==============================================================================

"""
PASO 1: Agregar imports (día 1)
├─ from hybrid_rag import HybridRAGEngine, HybridRAGConfig
├─ from retrieval.chunks import Chunk
└─ Verificar que venv311 esté disponible

PASO 2: Crear RetrievalService (día 1)
├─ Crear backend/app/services/retrieval_service.py
├─ Implementar RetrievalService class
└─ Tests unitarios

PASO 3: Actualizar enhanced_rag.py (día 2)
├─ Reemplazar search() en OfficialDocumentLibrary
├─ Usar RetrievalService en __init__
└─ Tests de integración

PASO 4: Actualizar .env (día 2)
├─ Agregar ENABLE_HYBRID_RETRIEVAL=1
├─ Agregar weights configuration
└─ Documentar variables

PASO 5: Testing E2E (día 2)
├─ Ejecutar test_e2e.py con hybrid enabled
├─ Verificar relevancia mejora
└─ Medir latencia

PASO 6: Deployment (día 3)
├─ Gradual rollout: 5% → 10% → 25% → 100%
├─ Monitorear user feedback
└─ A/B testing resultados
"""

# ==============================================================================
# PUNTOS DE INTEGRACIÓN CRÍTICOS
# ==============================================================================

"""
1. INICIALIZACIÓN
   ├─ Dónde: __init__ de OfficialDocumentLibrary
   ├─ Qué: Crear HybridRAGEngine si ENABLE_HYBRID_RETRIEVAL=True
   └─ Importante: NO indexar hasta que haya documentos

2. INDEXACIÓN
   ├─ Dónde: search() (lazy) o initialize() (eager)
   ├─ Qué: Convertir documentos a Chunks e indexar
   └─ Importante: Una sola vez, guardar en self._hybrid_indexed

3. BÚSQUEDA
   ├─ Dónde: search() method
   ├─ Qué: Llamar self._hybrid_engine.search(query, top_k)
   └─ Importante: Manejar excepciones, fallback a BM25

4. RESULTADOS
   ├─ Dónde: Formato de output
   ├─ Qué: Asegurar {id, source, title, content, score, language_detected}
   └─ Importante: score debe estar en [0, 1]

5. CITATION GUARD
   ├─ Dónde: search_and_generate() línea ~1362
   ├─ Qué: Pasar results con .content y .score
   └─ Importante: Ya está implementado, solo verifica formato
"""

# ==============================================================================
# VALIDACIÓN POST-INTEGRACIÓN
# ==============================================================================

"""
CHECKLIST:
└─ [ ] HybridRAGEngine imports correctamente
├─ [ ] Chunks se crean correctamente
├─ [ ] Indexación sin errores
├─ [ ] Búsqueda retorna List[Dict]
├─ [ ] Scores en rango [0, 1]
├─ [ ] Languague_detected es correcto
├─ [ ] Results formateados para citation_guard
├─ [ ] Fallback a BM25 funciona
├─ [ ] No hay regressions de latencia
└─ [ ] Tests E2E pasan

TESTS A EJECUTAR:
├─ pytest backend/tests/test_integration_phase4.py  # 15 tests
├─ pytest backend/tests/test_e2e.py                  # Full flow
├─ pytest backend/tests/test_grounding_*.py          # Grounding still works
└─ Benchmark antes/después                           # Comparar mejoras
"""

# ==============================================================================
# TROUBLESHOOTING
# ==============================================================================

"""
ERROR: "No module named 'sentence_transformers'"
→ Solución: Asegurar venv311 activado, pip install -r requirements-dev.txt

ERROR: "Chunks not found"
→ Solución: Verificar que _documents_to_chunks() se llama antes de search()

ERROR: "Score outside [0,1]"
→ Solución: Verificar score_fusion() en retrieval/rerank.py

ERROR: "Dense retriever failed, using BM25"
→ Solución: Esperado - graceful degradation funciona, pero verificar logs

LATENCIA ALTA (>500ms):
→ Solución: Implementar caché (Fase 5), o reducir candidate_multiplier
"""

# ==============================================================================
# ROLLBACK PLAN
# ==============================================================================

"""
Si Hybrid no funciona bien en producción:

1. RÁPIDO (minutos)
   └─ Set ENABLE_HYBRID_RETRIEVAL=0
   ├─ Redeployar (sin cambios de código)
   └─ Vuelve a BM25-only automáticamente

2. GRADUAL (horas)
   └─ Reducir porcentaje de usuarios con Hybrid
   ├─ HYBRID_ROLLOUT_PERCENTAGE=10 → 5 → 0
   └─ Monitorear mejora

3. INVESTIGACIÓN (días)
   └─ Revisar logs
   ├─ Ejecutar benchmark nuevamente
   ├─ Ajustar configuración
   └─ Re-test en staging
"""

# ==============================================================================
# FINAL CHECKLIST PARA INTEGRATION
# ==============================================================================

FINAL_INTEGRATION_CHECKLIST = """
PRE-INTEGRACIÓN:
- [ ] Leíste FASE_4_INTEGRACION_BENCHMARKING.md completo
- [ ] Ejecutaste benchmark_phase4.py y entiendes resultados
- [ ] Ejecutaste test_integration_phase4.py (15 tests pasando)
- [ ] Entiendes HybridRAGEngine API completamente
- [ ] Tienes venv311 funcionando

DURANTE-INTEGRACIÓN:
- [ ] Agregaste imports correctamente
- [ ] Función _documents_to_chunks() está correcta
- [ ] HybridRAGEngine se inicializa en __init__ o search()
- [ ] Manejo de excepciones con fallback a BM25
- [ ] Formato de output coincide con citation_guard expectations

POST-INTEGRACIÓN:
- [ ] Tests unitarios pasan (retrieval_service_test.py)
- [ ] Tests de integración pasan (test_e2e.py)
- [ ] test_grounding_*.py sigue pasando (citation guard compatible)
- [ ] Latencia medida y documentada
- [ ] Mejora de relevancia confirmada
- [ ] Graceful degradation testeada

DEPLOYMENT:
- [ ] Documentación de .env variables
- [ ] Rollback plan comunicado
- [ ] Monitoring metrics configurado
- [ ] A/B test plan listo
- [ ] User communication prepared
"""

print(__doc__)
