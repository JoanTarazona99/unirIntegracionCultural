"""
FASE 5: RE-BENCHMARKING LITE (Memory-Safe)
Comparar Phase 4 (baseline) vs Phase 5 (optimized)
Con protección contra segmentation faults por sobrecarga de memoria
"""

import sys
import gc
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.hybrid import HybridRetriever
from retrieval.model_warmer import ModelWarmer, warm_models_background
from retrieval.embedding_cache import EmbeddingCache
from retrieval.latency_monitor import LatencyMonitor


class ReBenchmarkDataset:
    """Dataset para re-benchmarking"""
    
    # 5 queries en español (común en usuarios)
    QUERIES = [
        "Costo de visa de estudiante en Rusia",
        "Cuánto tiempo tarda tramitar documentos",
        "Requisitos para estudiar en KubGU",
        "Dónde registrarse como extranjero",
        "Alojamiento para estudiantes internacionales",
    ]
    
    # 5 chunks multilingües (con contexto relevante)
    CHUNKS = [
        "La visa de estudiante en Rusia cuesta aproximadamente 200-300 rublos. El proceso toma 10-15 días hábiles.",
        "Los documentos requeridos incluyen pasaporte válido, certificado de aceptación, y comprobante de fondos.",
        "Universidad Estatal de Kubán ofrece programas para estudiantes internacionales desde hace 30 años.",
        "El registro con MVD debe completarse dentro de 7 días de llegada al país.",
        "El alojamiento en dormitorios cuesta 1,500-3,000 rublos por mes para estudiantes internacionales.",
    ]


class Phase5ReBenchmarkLite:
    """Re-benchmark LITE con protección de memoria"""
    
    def __init__(self, iterations: int = 5):
        """
        iterations: Número de iteraciones por query
                   Reducido a 5 vs 20 para evitar sobrecarga de memoria
        """
        self.dataset = ReBenchmarkDataset()
        self.iterations = iterations
        self.phase4_results = {}
        self.phase5_results = {}
        
    def run(self):
        """Ejecutar benchmark completo"""
        print("\n" + "=" * 80)
        print("FASE 5: RE-BENCHMARKING LITE (Memory-Safe)")
        print("=" * 80)
        
        print(f"\n[CONFIG]")
        print(f"  Queries: {len(self.dataset.QUERIES)}")
        print(f"  Chunks: {len(self.dataset.CHUNKS)}")
        print(f"  Iteraciones: {self.iterations} (lite)")
        print(f"  Memory Protection: ENABLED")
        
        # Phase 4: Sin optimizaciones
        print(f"\n[Phase 1/2] Benchmarking Phase 4 (Sin optimizaciones)...")
        self._benchmark_phase4()
        gc.collect()  # Limpiar memoria
        
        time.sleep(2)  # Esperar
        
        # Phase 5: Con optimizaciones
        print(f"\n[Phase 2/2] Benchmarking Phase 5 (Con optimizaciones)...")
        self._benchmark_phase5()
        gc.collect()  # Limpiar memoria
        
        # Análisis y reporte
        print(f"\n[Analysis] Analizando resultados...")
        self._analyze_and_report()
        
    def _benchmark_phase4(self):
        """Phase 4: HybridRetriever sin optimizaciones"""
        retriever = HybridRetriever(enable_warmer=False, enable_cache=False)
        retriever.index_documents(self.dataset.CHUNKS)
        
        latencies = []
        relevances = []
        
        for q_idx, query in enumerate(self.dataset.QUERIES):
            print(f"  Query {q_idx+1}/5: {query[:50]}...", end="")
            
            query_latencies = []
            for iter_idx in range(self.iterations):
                start = time.perf_counter()
                try:
                    results = retriever.search(query, top_k=3)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    query_latencies.append(elapsed_ms)
                    
                    # Estimar relevancia (0-1)
                    relevance = self._estimate_relevance(query, results)
                    relevances.append(relevance)
                except Exception as e:
                    print(f"\n    ERROR en iteración {iter_idx}: {e}")
                    continue
            
            if query_latencies:
                latencies.extend(query_latencies)
                avg_latency = np.mean(query_latencies)
                p95_latency = np.percentile(query_latencies, 95)
                print(f" OK (avg={avg_latency:.1f}ms, p95={p95_latency:.1f}ms)")
        
        # Guardar resultados
        self.phase4_results = {
            "mean_latency": float(np.mean(latencies)) if latencies else 0,
            "p95_latency": float(np.percentile(latencies, 95)) if len(latencies) > 1 else 0,
            "p99_latency": float(np.percentile(latencies, 99)) if len(latencies) > 1 else 0,
            "min_latency": float(np.min(latencies)) if latencies else 0,
            "max_latency": float(np.max(latencies)) if latencies else 0,
            "relevance": float(np.mean(relevances)) if relevances else 0,
            "count": len(latencies),
        }
        
        print(f"  Phase 4 Summary:")
        print(f"    Mean: {self.phase4_results['mean_latency']:.1f}ms")
        print(f"    P95:  {self.phase4_results['p95_latency']:.1f}ms")
        print(f"    Relevance: {self.phase4_results['relevance']:.2f}")
        
        # Limpiar
        del retriever
        gc.collect()
        
    def _benchmark_phase5(self):
        """Phase 5: HybridRetriever con optimizaciones"""
        # Inicializar con optimizaciones
        warmer = warm_models_background()
        time.sleep(1)  # Esperar a que carguen modelos
        
        retriever = HybridRetriever(enable_warmer=True, enable_cache=True)
        retriever.index_documents(self.dataset.CHUNKS)
        
        latencies = []
        relevances = []
        
        for q_idx, query in enumerate(self.dataset.QUERIES):
            print(f"  Query {q_idx+1}/5: {query[:50]}...", end="")
            
            query_latencies = []
            for iter_idx in range(self.iterations):
                start = time.perf_counter()
                try:
                    results = retriever.search(query, top_k=3)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    query_latencies.append(elapsed_ms)
                    
                    # Estimar relevancia
                    relevance = self._estimate_relevance(query, results)
                    relevances.append(relevance)
                except Exception as e:
                    print(f"\n    ERROR en iteración {iter_idx}: {e}")
                    continue
            
            if query_latencies:
                latencies.extend(query_latencies)
                avg_latency = np.mean(query_latencies)
                p95_latency = np.percentile(query_latencies, 95)
                print(f" OK (avg={avg_latency:.1f}ms, p95={p95_latency:.1f}ms)")
        
        # Guardar resultados
        self.phase5_results = {
            "mean_latency": float(np.mean(latencies)) if latencies else 0,
            "p95_latency": float(np.percentile(latencies, 95)) if len(latencies) > 1 else 0,
            "p99_latency": float(np.percentile(latencies, 99)) if len(latencies) > 1 else 0,
            "min_latency": float(np.min(latencies)) if latencies else 0,
            "max_latency": float(np.max(latencies)) if latencies else 0,
            "relevance": float(np.mean(relevances)) if relevances else 0,
            "count": len(latencies),
        }
        
        print(f"  Phase 5 Summary:")
        print(f"    Mean: {self.phase5_results['mean_latency']:.1f}ms")
        print(f"    P95:  {self.phase5_results['p95_latency']:.1f}ms")
        print(f"    Relevance: {self.phase5_results['relevance']:.2f}")
        
        # Limpiar
        del retriever
        gc.collect()
    
    def _estimate_relevance(self, query: str, results: List[Dict]) -> float:
        """Estimar relevancia simple basada en matches"""
        if not results:
            return 0.0
        
        query_words = set(query.lower().split())
        relevances = []
        
        for result in results:
            text = result.get('text', '').lower()
            text_words = set(text.split())
            
            # Jaccard similarity
            if text_words:
                intersection = len(query_words & text_words)
                union = len(query_words | text_words)
                relevance = intersection / union if union > 0 else 0.0
                relevances.append(relevance)
        
        return np.mean(relevances) if relevances else 0.0
    
    def _analyze_and_report(self):
        """Analizar y reportar resultados"""
        print("\n" + "=" * 80)
        print("COMPARATIVE ANALYSIS: Phase 4 vs Phase 5")
        print("=" * 80)
        
        p4_p95 = self.phase4_results.get('p95_latency', 0)
        p5_p95 = self.phase5_results.get('p95_latency', 0)
        
        if p4_p95 > 0:
            improvement_pct = ((p4_p95 - p5_p95) / p4_p95) * 100
        else:
            improvement_pct = 0
        
        p4_relevance = self.phase4_results.get('relevance', 0)
        p5_relevance = self.phase5_results.get('relevance', 0)
        relevance_change = ((p5_relevance - p4_relevance) / p4_relevance * 100) if p4_relevance > 0 else 0
        
        print(f"\n[LATENCY P95]")
        print(f"  Phase 4 (Baseline):  {p4_p95:7.1f} ms")
        print(f"  Phase 5 (Optimized): {p5_p95:7.1f} ms")
        print(f"  Improvement:         {improvement_pct:7.1f}% ↓")
        
        print(f"\n[LATENCY MEAN]")
        p4_mean = self.phase4_results.get('mean_latency', 0)
        p5_mean = self.phase5_results.get('mean_latency', 0)
        if p4_mean > 0:
            mean_improvement = ((p4_mean - p5_mean) / p4_mean) * 100
        else:
            mean_improvement = 0
        print(f"  Phase 4 (Baseline):  {p4_mean:7.1f} ms")
        print(f"  Phase 5 (Optimized): {p5_mean:7.1f} ms")
        print(f"  Improvement:         {mean_improvement:7.1f}% ↓")
        
        print(f"\n[RELEVANCE]")
        print(f"  Phase 4: {p4_relevance:.2f}")
        print(f"  Phase 5: {p5_relevance:.2f}")
        print(f"  Change:  {relevance_change:+.1f}%")
        
        # Recomendación
        print(f"\n[RECOMMENDATION]")
        if improvement_pct >= 50 and relevance_change >= -5:
            recommendation = "✅ PRODUCTION READY"
            details = f"Latency improved {improvement_pct:.0f}%, relevance stable"
        elif improvement_pct >= 25 and relevance_change >= -10:
            recommendation = "🟡 BETA READY"
            details = f"Solid improvement ({improvement_pct:.0f}%), monitor closely"
        else:
            recommendation = "🔴 NEEDS OPTIMIZATION"
            details = f"Improvement {improvement_pct:.0f}% insufficient or relevance degraded"
        
        print(f"  Status: {recommendation}")
        print(f"  Details: {details}")
        
        # Guardar resultados a JSON
        output_file = Path(__file__).parent / "re_benchmark_phase5_results.json"
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "iterations": self.iterations,
            "phase4": self.phase4_results,
            "phase5": self.phase5_results,
            "improvement_pct": improvement_pct,
            "relevance_change_pct": relevance_change,
            "recommendation": recommendation,
            "details": details,
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n[OUTPUT]")
        print(f"  Results saved to: {output_file}")
        print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        benchmark = Phase5ReBenchmarkLite(iterations=5)
        benchmark.run()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except SegmentationFault:
        print("\n❌ Segmentation fault - memoria insuficiente")
        print("Solución: Reducir iteraciones o usar máquina con más RAM")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
