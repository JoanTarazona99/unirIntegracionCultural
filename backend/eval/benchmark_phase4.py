"""
Fase 4: Benchmarking - Compare BM25 vs Hybrid (BM25 + Dense + Rerank)

Run: ./venv311/Scripts/python.exe backend/eval/benchmark_phase4.py
"""

import sys
from pathlib import Path
import json
import time
from typing import List, Dict, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.sparse import BM25Retriever
from retrieval.dense import DenseRetriever
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import CrossEncoderReranker, QueryLanguageDetector
from retrieval.chunks import Chunk


class BenchmarkDataset:
    """Test dataset for benchmarking"""
    
    def __init__(self):
        self.chunks = self._load_chunks()
        self.queries = self._load_queries()
    
    def _load_chunks(self) -> List[Chunk]:
        """Load sample chunks in multiple languages"""
        return [
            Chunk(
                id="visa_reqs_es",
                source="MVD",
                title="Requisitos de Visa de Estudiante",
                content="Para obtener una visa de estudiante en Rusia necesitas: 1) Pasaporte válido por 18 meses. 2) Certificado de nivel B1 de ruso. 3) Documentos de KubGU. 4) Seguro médico válido. 5) Prueba de solvencia económica ($300-400/mes).",
            ),
            Chunk(
                id="course_duration_es",
                source="KubGU",
                title="Duración del Curso Preparatorio",
                content="El curso preparatorio de ruso en KubGU dura 3-6 meses dependiendo del nivel inicial. Estudiantes principiantes (A1) típicamente completan en 6 meses. Estudiantes intermedios (A2-B1) pueden completar en 3-4 meses. Las clases son 20-25 horas por semana.",
            ),
            Chunk(
                id="course_cost_es",
                source="KubGU",
                title="Costo del Curso",
                content="El costo del curso preparatorio de ruso es aproximadamente 50,000-100,000 rublos por semestre (2-3 meses). Esto incluye: libro de texto, acceso a material digital, examen final. No incluye alojamiento. Descuentos disponibles para estudiantes de países de la CIS.",
            ),
            Chunk(
                id="registration_process_es",
                source="AdminOffice",
                title="Proceso de Registración",
                content="Para registrarse como estudiante en KubGU: 1) Llenar formulario online. 2) Enviar pasaporte escanizado. 3) Pagar matrícula. 4) Obtener número de estudiante. 5) Recibir información de orientación. El proceso toma 5-7 días hábiles después de pago completo.",
            ),
            Chunk(
                id="housing_options_es",
                source="Housing",
                title="Opciones de Alojamiento",
                content="KubGU ofrece alojamiento en 5 dormitorios modernos. Costo: 3,000-5,000 rublos/mes por habitación compartida. Incluye: internet, servicios, muebles. Estudiantes pueden también rentar apartamentos privados (5,000-10,000 rublos/mes). La mayoría de estudiantes vive en dormitorio 1-2 años, luego en apartamentos privados.",
            ),
            Chunk(
                id="language_levels_es",
                source="KubGU",
                title="Niveles de Ruso (MCER)",
                content="KubGU sigue el Marco Europeo de Referencia para Lenguas (MCER) con 6 niveles: A1 (Principiante), A2 (Básico), B1 (Intermedio), B2 (Intermedio-Alto), C1 (Avanzado), C2 (Dominio). Cada nivel requiere 120-150 horas de estudio. Certificado reconocido internacionalmente al completar.",
            ),
            Chunk(
                id="visa_reqs_ru",
                source="MVD",
                title="Требования для студенческой визы",
                content="Для получения студенческой визы в Россию вам нужны: 1) Действительный паспорт на 18 месяцев. 2) Сертификат уровня B1 русского языка. 3) Документы от КубГУ. 4) Полис медицинского страхования. 5) Доказательство финансовой состоятельности ($300-400 в месяц).",
            ),
            Chunk(
                id="course_duration_ru",
                source="KubGU",
                title="Продолжительность подготовительного курса",
                content="Подготовительный курс русского языка в КубГУ длится 3-6 месяцев в зависимости от начального уровня. Студенты уровня A1 обычно заканчивают за 6 месяцев. Студенты уровня A2-B1 могут закончить за 3-4 месяца. Занятия проводятся 20-25 часов в неделю.",
            ),
        ]
    
    def _load_queries(self) -> List[Dict]:
        """Load queries with expected relevant chunks"""
        return [
            {
                "query_es": "¿Cuánto cuesta el curso de ruso?",
                "query_en": "How much does the Russian course cost?",
                "query_ru": "Сколько стоит курс русского языка?",
                "expected_chunks": ["course_cost_es"],
                "language": "es"
            },
            {
                "query_es": "Requisitos para obtener visa de estudiante",
                "query_en": "What are the requirements for a student visa?",
                "query_ru": "Каковы требования для студенческой визы?",
                "expected_chunks": ["visa_reqs_es", "visa_reqs_ru"],
                "language": "es"
            },
            {
                "query_es": "¿Cuánto tiempo dura el curso preparatorio?",
                "query_en": "How long is the preparatory course?",
                "query_ru": "Как долго длится подготовительный курс?",
                "expected_chunks": ["course_duration_es", "course_duration_ru"],
                "language": "es"
            },
            {
                "query_es": "Cómo registrarse como estudiante",
                "query_en": "How to register as a student?",
                "query_ru": "Как зарегистрироваться в качестве студента?",
                "expected_chunks": ["registration_process_es"],
                "language": "es"
            },
            {
                "query_es": "Opciones de alojamiento y costos",
                "query_en": "What are the housing options?",
                "query_ru": "Какие есть варианты жилья?",
                "expected_chunks": ["housing_options_es"],
                "language": "es"
            },
        ]


class BenchmarkRunner:
    """Run benchmarks comparing retrieval strategies"""
    
    def __init__(self):
        self.dataset = BenchmarkDataset()
        self.results = {
            "bm25": [],
            "hybrid": [],
        }
    
    def run(self):
        """Run full benchmark"""
        print("\n" + "="*80)
        print("FASE 4: BENCHMARKING - BM25 vs HYBRID RETRIEVAL")
        print("="*80)
        
        # Index dataset
        print("\n[1/3] Indexing chunks...")
        self.dataset.chunks  # Already loaded
        
        # Benchmark BM25
        print("[2/3] Benchmarking BM25-only retrieval...")
        self._benchmark_bm25()
        
        # Benchmark Hybrid
        print("[3/3] Benchmarking Hybrid (BM25 + Dense + Rerank) retrieval...")
        self._benchmark_hybrid()
        
        # Print results
        self._print_results()
    
    def _benchmark_bm25(self):
        """Benchmark BM25 retriever"""
        retriever = BM25Retriever()
        retriever.index(self.dataset.chunks)
        
        detector = QueryLanguageDetector()
        
        for test_case in self.dataset.queries:
            query = test_case["query_es"]
            expected = set(test_case["expected_chunks"])
            lang = test_case["language"]
            
            # Measure retrieval time
            start = time.time()
            results = retriever.search(query, top_k=3)
            elapsed = time.time() - start
            
            # Calculate metrics
            retrieved_ids = {r.chunk.id for r in results}
            relevance_score = len(retrieved_ids & expected) / len(expected) if expected else 0
            
            self.results["bm25"].append({
                "query": query,
                "time_ms": elapsed * 1000,
                "relevance": relevance_score,
                "retrieved_count": len(results),
                "language": detector.detect(query),
            })
    
    def _benchmark_hybrid(self):
        """Benchmark Hybrid retriever"""
        sparse = BM25Retriever()
        dense = DenseRetriever()
        reranker = CrossEncoderReranker()
        
        retriever = HybridRetriever(
            sparse=sparse,
            dense=dense,
            reranker=reranker,
        )
        retriever.index(self.dataset.chunks)
        
        detector = QueryLanguageDetector()
        
        for test_case in self.dataset.queries:
            query = test_case["query_es"]
            expected = set(test_case["expected_chunks"])
            lang = test_case["language"]
            
            # Measure retrieval time
            start = time.time()
            results = retriever.search(query, top_k=3)
            elapsed = time.time() - start
            
            # Calculate metrics
            retrieved_ids = {r.chunk.id for r in results}
            relevance_score = len(retrieved_ids & expected) / len(expected) if expected else 0
            
            self.results["hybrid"].append({
                "query": query,
                "time_ms": elapsed * 1000,
                "relevance": relevance_score,
                "retrieved_count": len(results),
                "language": detector.detect(query),
            })
    
    def _print_results(self):
        """Print and compare results"""
        print("\n" + "="*80)
        print("RESULTADOS DEL BENCHMARKING")
        print("="*80)
        
        print("\n[BM25-ONLY (Baseline)]")
        bm25_relevance = []
        bm25_times = []
        for i, result in enumerate(self.results["bm25"], 1):
            print(f"Query {i}: {result['query'][:50]}...")
            print(f"  Relevance: {result['relevance']:.1%} | Time: {result['time_ms']:.1f}ms")
            bm25_relevance.append(result['relevance'])
            bm25_times.append(result['time_ms'])
        
        avg_bm25_relevance = sum(bm25_relevance) / len(bm25_relevance) if bm25_relevance else 0
        avg_bm25_time = sum(bm25_times) / len(bm25_times) if bm25_times else 0
        
        print(f"\nAverage Relevance: {avg_bm25_relevance:.1%}")
        print(f"Average Time: {avg_bm25_time:.1f}ms")
        
        print("\n[HYBRID (BM25 + Dense + Rerank)]")
        hybrid_relevance = []
        hybrid_times = []
        for i, result in enumerate(self.results["hybrid"], 1):
            print(f"Query {i}: {result['query'][:50]}...")
            print(f"  Relevance: {result['relevance']:.1%} | Time: {result['time_ms']:.1f}ms")
            hybrid_relevance.append(result['relevance'])
            hybrid_times.append(result['time_ms'])
        
        avg_hybrid_relevance = sum(hybrid_relevance) / len(hybrid_relevance) if hybrid_relevance else 0
        avg_hybrid_time = sum(hybrid_times) / len(hybrid_times) if hybrid_times else 0
        
        print(f"\nAverage Relevance: {avg_hybrid_relevance:.1%}")
        print(f"Average Time: {avg_hybrid_time:.1f}ms")
        
        # Calculate improvements
        print("\n[MEJORAS (Hybrid vs BM25)]")
        
        relevance_improvement = (avg_hybrid_relevance - avg_bm25_relevance) / avg_bm25_relevance if avg_bm25_relevance > 0 else 0
        time_increase = (avg_hybrid_time - avg_bm25_time) / avg_bm25_time if avg_bm25_time > 0 else 0
        
        print(f"Relevance Improvement: {relevance_improvement:+.1%}")
        print(f"Time Increase: {time_increase:+.1%}")
        print(f"\nConclusion:")
        if relevance_improvement > 0:
            print(f"[+] Hybrid retrieval is {relevance_improvement:.1%} more relevant")
        else:
            print(f"[-] Hybrid retrieval is {abs(relevance_improvement):.1%} less relevant")
        
        if time_increase > 1:
            print(f"[!] But takes {time_increase:.1%} more time (due to cross-encoder)")
        else:
            print(f"[+] With minimal time overhead ({time_increase:.1%})")
        
        # Save results
        self._save_results(avg_bm25_relevance, avg_hybrid_relevance, avg_bm25_time, avg_hybrid_time)
    
    def _save_results(self, bm25_rel, hybrid_rel, bm25_time, hybrid_time):
        """Save benchmark results to JSON"""
        results_file = Path(__file__).parent.parent / "data" / "eval" / "benchmark_results_phase4.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "timestamp": time.time(),
            "bm25": {
                "avg_relevance": bm25_rel,
                "avg_time_ms": bm25_time,
            },
            "hybrid": {
                "avg_relevance": hybrid_rel,
                "avg_time_ms": hybrid_time,
            },
            "improvement": {
                "relevance_pct": (hybrid_rel - bm25_rel) / bm25_rel if bm25_rel > 0 else 0,
                "time_overhead_pct": (hybrid_time - bm25_time) / bm25_time if bm25_time > 0 else 0,
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n[+] Results saved to {results_file}")


if __name__ == "__main__":
    runner = BenchmarkRunner()
    runner.run()
