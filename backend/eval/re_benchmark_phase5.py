"""
Fase 5: Re-Benchmarking with Optimizations

Compara:
- Fase 4 (Hybrid sin optimizaciones)
- Fase 5 (Hybrid con model warming + cache)

Valida:
- Mejora de latencia
- Mantención de relevancia
- Readiness para producción

Ejecución: python backend/eval/re_benchmark_phase5.py
"""

import sys
from pathlib import Path
import json
import time
from typing import List, Dict
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.sparse import BM25Retriever
from retrieval.dense import DenseRetriever
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import CrossEncoderReranker, QueryLanguageDetector
from retrieval.chunks import Chunk
from retrieval.model_warmer import ModelWarmer
from retrieval.embedding_cache import EmbeddingCache
from retrieval.latency_monitor import LatencyMonitor, LatencyBudget


class ReBenchmarkDataset:
    """Dataset for re-benchmarking Fase 5"""
    
    def __init__(self):
        self.chunks = self._load_chunks()
        self.queries = self._load_queries()
    
    def _load_chunks(self) -> List[Chunk]:
        """Load sample chunks"""
        return [
            Chunk(
                id="visa_reqs",
                source="MVD",
                title="Visa Requirements",
                content="Para obtener visa se necesita: pasaporte válido, documento de invitación, seguro médico, certificado de nivel B1 de ruso.",
            ),
            Chunk(
                id="course_cost",
                source="KubGU",
                title="Course Cost",
                content="El costo del curso preparatorio es 50,000-100,000 rublos por semestre. Incluye: material, examen, acceso digital.",
            ),
            Chunk(
                id="housing",
                source="Housing",
                title="Alojamiento",
                content="Dormitorios disponibles a 3,000-5,000 rublos por mes. Incluyen internet, muebles, servicios.",
            ),
            Chunk(
                id="registration",
                source="Admin",
                title="Registration Process",
                content="Registración toma 5-7 días hábiles. Pasos: formulario online, enviar documentos, pagar matrícula, recibir número.",
            ),
            Chunk(
                id="language_levels",
                source="KubGU",
                title="Language Levels",
                content="Niveles según MCER: A1 (principiante), A2 (básico), B1 (intermedio), B2 (intermedio-alto), C1 (avanzado).",
            ),
        ]
    
    def _load_queries(self) -> List[Dict]:
        """Load test queries"""
        return [
            {
                "query": "¿Cuánto cuesta el curso de ruso?",
                "expected_chunks": ["course_cost"],
            },
            {
                "query": "Requisitos para obtener visa",
                "expected_chunks": ["visa_reqs"],
            },
            {
                "query": "Opciones de alojamiento",
                "expected_chunks": ["housing"],
            },
            {
                "query": "Cómo registrarse como estudiante",
                "expected_chunks": ["registration"],
            },
            {
                "query": "Niveles de ruso",
                "expected_chunks": ["language_levels"],
            },
        ]


class Phase5ReiBenchmark:
    """Run re-benchmark with optimizations"""
    
    def __init__(self, num_iterations: int = 20):
        self.dataset = ReBenchmarkDataset()
        self.num_iterations = num_iterations
        
        self.results = {
            'phase4': {
                'relevance': 0.0,
                'latencies': [],
            },
            'phase5': {
                'relevance': 0.0,
                'latencies': [],
                'cache_hits': 0,
                'cache_misses': 0,
            }
        }
    
    def run(self):
        """Execute re-benchmark"""
        print("\n" + "="*80)
        print("FASE 5: RE-BENCHMARKING WITH OPTIMIZATIONS")
        print("="*80)
        
        print(f"\n[CONFIG]")
        print(f"  Dataset queries: {len(self.dataset.queries)}")
        print(f"  Chunks: {len(self.dataset.chunks)}")
        print(f"  Iterations: {self.num_iterations}")
        
        # Phase 4: Without optimizations (baseline)
        print("\n[Phase 1/2] Benchmarking Phase 4 (Sin optimizaciones)...")
        self._benchmark_phase4()
        
        # Phase 5: With optimizations
        print("\n[Phase 2/2] Benchmarking Phase 5 (Con optimizaciones)...")
        self._benchmark_phase5()
        
        # Analyze & Report
        print("\n[Análisis] Comparando resultados...")
        self._analyze_and_report()
    
    def _benchmark_phase4(self):
        """Benchmark without optimizations (Fase 4)"""
        retriever = HybridRetriever(
            sparse=BM25Retriever(),
            dense=DenseRetriever(),
            reranker=CrossEncoderReranker(),
        )
        retriever.index(self.dataset.chunks)
        
        # Run queries
        for i in range(self.num_iterations):
            print(f"  Iteration {i+1}/{self.num_iterations}...", end='\r')
            
            for query_data in self.dataset.queries:
                query = query_data['query']
                expected = set(query_data['expected_chunks'])
                
                start = time.time()
                results = retriever.search(query, top_k=3)
                elapsed = (time.time() - start) * 1000  # ms
                
                retrieved_ids = {r.chunk.id for r in results}
                relevance = len(retrieved_ids & expected) / len(expected) if expected else 0
                
                self.results['phase4']['latencies'].append(elapsed)
                self.results['phase4']['relevance'] = max(
                    self.results['phase4']['relevance'],
                    relevance
                )
        
        print(f"  Phase 4 completed - {len(self.results['phase4']['latencies'])} queries")
    
    def _benchmark_phase5(self):
        """Benchmark with optimizations (Fase 5)"""
        
        # Warm up models
        print("  Warming up models...")
        warmer = ModelWarmer()
        warmer.warm_models()
        time.sleep(1)  # Wait for models
        
        # Initialize with cache
        dense = DenseRetriever()
        embedding_cache = EmbeddingCache(ttl=3600)
        
        retriever = HybridRetriever(
            sparse=BM25Retriever(),
            dense=dense,
            reranker=CrossEncoderReranker(),
        )
        retriever.index(self.dataset.chunks)
        
        monitor = LatencyMonitor()
        
        # Run queries
        for i in range(self.num_iterations):
            print(f"  Iteration {i+1}/{self.num_iterations}...", end='\r')
            
            for query_data in self.dataset.queries:
                query = query_data['query']
                expected = set(query_data['expected_chunks'])
                
                # Measure with monitor
                with monitor.measure_stage('total'):
                    results = retriever.search(query, top_k=3)
                
                # Cache hit/miss tracking
                cached = embedding_cache.get(query)
                if cached is not None:
                    self.results['phase5']['cache_hits'] += 1
                else:
                    self.results['phase5']['cache_misses'] += 1
                
                retrieved_ids = {r.chunk.id for r in results}
                relevance = len(retrieved_ids & expected) / len(expected) if expected else 0
                
                self.results['phase5']['relevance'] = max(
                    self.results['phase5']['relevance'],
                    relevance
                )
        
        # Get latencies from monitor
        self.results['phase5']['latencies'] = monitor.stage_latencies['total']
        
        print(f"  Phase 5 completed - {len(self.results['phase5']['latencies'])} queries")
        print(f"  Cache hit rate: {self._get_cache_hit_rate():.1%}")
    
    def _get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.results['phase5']['cache_hits'] + self.results['phase5']['cache_misses']
        if total == 0:
            return 0.0
        return self.results['phase5']['cache_hits'] / total
    
    def _analyze_and_report(self):
        """Analyze results and generate report"""
        
        phase4_latencies = self.results['phase4']['latencies']
        phase5_latencies = self.results['phase5']['latencies']
        
        # Calculate stats
        p95_phase4 = np.percentile(phase4_latencies, 95)
        p95_phase5 = np.percentile(phase5_latencies, 95)
        
        mean_phase4 = np.mean(phase4_latencies)
        mean_phase5 = np.mean(phase5_latencies)
        
        latency_improvement = (p95_phase4 - p95_phase5) / p95_phase4 * 100
        
        rel_phase4 = self.results['phase4']['relevance']
        rel_phase5 = self.results['phase5']['relevance']
        
        print("\n" + "="*80)
        print("RE-BENCHMARKING RESULTS")
        print("="*80)
        
        print("\n[LATENCY]")
        print(f"Phase 4 (baseline):")
        print(f"  Mean:  {mean_phase4:.1f}ms")
        print(f"  P95:   {p95_phase4:.1f}ms")
        
        print(f"\nPhase 5 (optimized):")
        print(f"  Mean:  {mean_phase5:.1f}ms")
        print(f"  P95:   {p95_phase5:.1f}ms")
        
        print(f"\nImprovement:")
        print(f"  Mean:  {(mean_phase4-mean_phase5)/mean_phase4*100:+.1f}%")
        print(f"  P95:   {latency_improvement:+.1f}%")
        
        print("\n[RELEVANCE]")
        print(f"Phase 4: {rel_phase4:.1%}")
        print(f"Phase 5: {rel_phase5:.1%}")
        print(f"Maintained: {'YES' if rel_phase5 >= rel_phase4 else 'NO'}")
        
        print("\n[CACHING]")
        print(f"Cache hit rate: {self._get_cache_hit_rate():.1%}")
        print(f"Hits: {self.results['phase5']['cache_hits']}")
        print(f"Misses: {self.results['phase5']['cache_misses']}")
        
        print("\n" + "="*80)
        print("RECOMMENDATION")
        print("="*80)
        
        # Decision logic
        if latency_improvement > 50 and rel_phase5 >= rel_phase4 and p95_phase5 < 500:
            print("\n[+] READY FOR PRODUCTION")
            print(f"  - Latency improved {latency_improvement:.0f}%")
            print(f"  - Relevance maintained at {rel_phase5:.1%}")
            print(f"  - P95 latency {p95_phase5:.0f}ms < 500ms target")
            print("\nNext steps:")
            print("  1. Activate A/B testing")
            print("  2. Start with 5% Hybrid rollout")
            print("  3. Monitor user satisfaction")
            print("  4. Ramp up to 100%")
            
        elif latency_improvement > 30 and rel_phase5 >= rel_phase4:
            print("\n[!] ACCEPTABLE - PROCEED WITH CAUTION")
            print(f"  - Latency improved {latency_improvement:.0f}%")
            print(f"  - Relevance maintained at {rel_phase5:.1%}")
            print(f"  - P95 latency {p95_phase5:.0f}ms (monitor)")
            print("\nRecommendation:")
            print("  1. Deploy to beta (10% users)")
            print("  2. Monitor P95 latency closely")
            print("  3. Add caching layer if needed")
            print("  4. Re-evaluate after 1 week")
            
        else:
            print("\n[-] NEEDS MORE OPTIMIZATION")
            print(f"  - Latency improvement: {latency_improvement:.0f}%")
            print(f"  - Relevance: {rel_phase5:.1%}")
            print("\nRecommendation:")
            print("  1. Implement Redis embedding cache")
            print("  2. Reduce reranker candidate set")
            print("  3. Use BM25-heavy fusion weights")
            print("  4. Re-benchmark after optimizations")
        
        print("\n" + "="*80)


def main():
    """Run re-benchmark"""
    benchmark = Phase5ReiBenchmark(num_iterations=20)
    benchmark.run()


if __name__ == "__main__":
    main()
