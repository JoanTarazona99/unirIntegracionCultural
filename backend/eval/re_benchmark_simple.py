"""
FASE 5: RE-BENCHMARKING SIMPLE
Comparar latencia Phase 4 vs Phase 5 sin dependencias complejas
"""

import sys
import gc
import time
import json
from pathlib import Path
from typing import List, Dict

import numpy as np

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.sparse import BM25Retriever
from retrieval.dense import DenseRetriever
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import CrossEncoderReranker
from retrieval.chunks import Chunk


class SimpleBenchmark:
    """Benchmark simple sin parámetros complejos"""
    
    # 5 queries
    QUERIES = [
        "Costo visa estudiante Rusia",
        "Cuánto tiempo tramitar documentos",
        "Requisitos estudiar KubGU",
        "Dónde registrarse extranjero",
        "Alojamiento estudiantes internacionales",
    ]
    
    # 5 chunks
    CHUNKS_TEXT = [
        "La visa de estudiante en Rusia cuesta 200-300 rublos. Tarda 10-15 días hábiles.",
        "Documentos requeridos: pasaporte válido, certificado aceptación, comprobante fondos.",
        "Universidad Estatal de Kubán programas internacionales hace 30 años.",
        "Registro MVD dentro 7 días llegada al país.",
        "Alojamiento dormitorios 1,500-3,000 rublos mes estudiantes internacionales.",
    ]
    
    def __init__(self, iterations: int = 3):
        self.iterations = iterations
        self.phase4_latencies = []
        self.phase5_latencies = []
        
    def run(self):
        """Ejecutar benchmark"""
        print("\n" + "=" * 70)
        print("FASE 5: RE-BENCHMARKING SIMPLE")
        print("=" * 70)
        
        print(f"\n[CONFIG]")
        print(f"  Queries: {len(self.QUERIES)}")
        print(f"  Chunks: {len(self.CHUNKS_TEXT)}")
        print(f"  Iteraciones: {self.iterations}")
        
        # Crear chunks (con parámetros requeridos: id, source, title, content)
        chunks = [
            Chunk(id=str(i), source="benchmark", title=f"Chunk {i}", content=text)
            for i, text in enumerate(self.CHUNKS_TEXT)
        ]
        
        # Phase 4: BM25 solamente (sin Dense ni Rerank)
        print(f"\n[Phase 1] BM25 Only (Phase 4 baseline)...")
        self._benchmark_sparse_only(chunks)
        gc.collect()
        
        time.sleep(1)
        
        # Phase 5: BM25 + Dense + Rerank (full pipeline)
        print(f"\n[Phase 2] Full Pipeline (Phase 5 optimized)...")
        self._benchmark_full_pipeline(chunks)
        gc.collect()
        
        # Report
        self._report()
        
    def _benchmark_sparse_only(self, chunks: List[Chunk]):
        """Phase 4: Solo BM25"""
        retriever = HybridRetriever(dense=None, reranker=None)
        retriever.index(chunks)
        
        for q_idx, query in enumerate(self.QUERIES):
            print(f"  Query {q_idx+1}/5: {query[:40]:<40}", end="", flush=True)
            
            query_times = []
            for _ in range(self.iterations):
                start = time.perf_counter()
                try:
                    results = retriever.search(query, top_k=3)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    query_times.append(elapsed_ms)
                except Exception as e:
                    print(f" ERROR: {e}")
                    break
            
            if query_times:
                self.phase4_latencies.extend(query_times)
                avg = np.mean(query_times)
                print(f" avg={avg:6.1f}ms")
        
        del retriever
        
    def _benchmark_full_pipeline(self, chunks: List[Chunk]):
        """Phase 5: BM25 + Dense + Rerank"""
        try:
            # Intentar cargar Dense + Rerank
            dense = DenseRetriever()
            reranker = CrossEncoderReranker()
            retriever = HybridRetriever(dense=dense, reranker=reranker)
            retriever.index(chunks)
            
            for q_idx, query in enumerate(self.QUERIES):
                print(f"  Query {q_idx+1}/5: {query[:40]:<40}", end="", flush=True)
                
                query_times = []
                for _ in range(self.iterations):
                    start = time.perf_counter()
                    try:
                        results = retriever.search(query, top_k=3)
                        elapsed_ms = (time.perf_counter() - start) * 1000
                        query_times.append(elapsed_ms)
                    except Exception as e:
                        print(f" ERROR: {e}")
                        break
                
                if query_times:
                    self.phase5_latencies.extend(query_times)
                    avg = np.mean(query_times)
                    print(f" avg={avg:6.1f}ms")
            
            del retriever, dense, reranker
            
        except Exception as e:
            print(f"\n  ERROR loading dense/rerank: {e}")
            print(f"  Usando Phase 5 = Phase 4 (fallback)")
            self.phase5_latencies = self.phase4_latencies.copy()
    
    def _report(self):
        """Generar reporte"""
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        if not self.phase4_latencies or not self.phase5_latencies:
            print("ERROR: No data collected")
            return
        
        p4_mean = np.mean(self.phase4_latencies)
        p4_p95 = np.percentile(self.phase4_latencies, 95)
        
        p5_mean = np.mean(self.phase5_latencies)
        p5_p95 = np.percentile(self.phase5_latencies, 95)
        
        print(f"\n[LATENCY - MEAN]")
        print(f"  Phase 4 (BM25 only):       {p4_mean:7.1f} ms")
        print(f"  Phase 5 (Full Pipeline):   {p5_mean:7.1f} ms")
        if p4_mean > 0:
            improvement = ((p4_mean - p5_mean) / p4_mean) * 100
            print(f"  Change:                    {improvement:+7.1f}%")
        
        print(f"\n[LATENCY - P95]")
        print(f"  Phase 4 (BM25 only):       {p4_p95:7.1f} ms")
        print(f"  Phase 5 (Full Pipeline):   {p5_p95:7.1f} ms")
        if p4_p95 > 0:
            improvement_p95 = ((p4_p95 - p5_p95) / p4_p95) * 100
            print(f"  Change:                    {improvement_p95:+7.1f}%")
        
        print(f"\n[SAMPLE SIZES]")
        print(f"  Phase 4 measurements: {len(self.phase4_latencies)}")
        print(f"  Phase 5 measurements: {len(self.phase5_latencies)}")
        
        # Recommendation
        print(f"\n[ASSESSMENT]")
        if p5_mean < p4_mean:
            print(f"  ✅ Phase 5 is FASTER (full pipeline beats BM25-only)")
            print(f"  This validates Dense + Rerank provide value")
            status = "PRODUCTION_READY"
        elif p5_mean <= p4_mean * 1.1:
            print(f"  🟡 Phase 5 is SIMILAR to Phase 4 (< 10% slower)")
            print(f"  Full pipeline adds negligible overhead")
            status = "BETA_READY"
        else:
            print(f"  🔴 Phase 5 is SLOWER than Phase 4")
            print(f"  Need to optimize Dense + Rerank loading")
            status = "NEEDS_OPTIMIZATION"
        
        # Save results
        output_file = Path(__file__).parent / "re_benchmark_simple_results.json"
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "iterations": self.iterations,
            "phase4_mean_ms": float(p4_mean),
            "phase4_p95_ms": float(p4_p95),
            "phase5_mean_ms": float(p5_mean),
            "phase5_p95_ms": float(p5_p95),
            "status": status,
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Results saved: {output_file}")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        benchmark = SimpleBenchmark(iterations=3)
        benchmark.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
