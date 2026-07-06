"""
Fase 4: Results Analysis - Analyze and visualize benchmarking results

Genera gráficos y análisis de los resultados de benchmarking.

Uso: ./venv311/Scripts/python.exe backend/eval/analyze_results_phase4.py
"""

import json
from pathlib import Path
from typing import Dict, Any


class ResultsAnalyzer:
    """Analyze Fase 4 benchmarking results"""
    
    def __init__(self):
        self.results_file = Path(__file__).parent.parent / "data" / "eval" / "benchmark_results_phase4.json"
    
    def load_results(self) -> Dict[str, Any]:
        """Load benchmark results from JSON"""
        if not self.results_file.exists():
            print(f"❌ Results file not found: {self.results_file}")
            return None
        
        with open(self.results_file) as f:
            return json.load(f)
    
    def analyze(self):
        """Run analysis"""
        print("\n" + "="*80)
        print("FASE 4: RESULTADOS DE BENCHMARKING - ANÁLISIS DETALLADO")
        print("="*80)
        
        results = self.load_results()
        if not results:
            return
        
        self._analyze_relevance(results)
        self._analyze_performance(results)
        self._analyze_trade_offs(results)
        self._generate_recommendations(results)
    
    def _analyze_relevance(self, results):
        """Analyze relevance improvements"""
        print("\n┌─ ANÁLISIS DE RELEVANCIA")
        print("│")
        
        bm25_rel = results['bm25']['avg_relevance']
        hybrid_rel = results['hybrid']['avg_relevance']
        improvement = results['improvement']['relevance_pct']
        
        print(f"│ BM25 Relevance:        {bm25_rel:.1%}")
        print(f"│ Hybrid Relevance:      {hybrid_rel:.1%}")
        print(f"│ Improvement:           {improvement:+.1%}")
        print("│")
        
        if improvement > 0:
            print(f"│ ✓ Hybrid es {abs(improvement):.1%} MÁS RELEVANTE")
            if improvement > 0.2:
                print(f"│   Este es un MEJORA SIGNIFICATIVA - recomendado para producción")
            elif improvement > 0.1:
                print(f"│   Mejora moderada - considera activar en etapas")
            else:
                print(f"│   Mejora pequeña - evalúa costo vs beneficio")
        else:
            print(f"│ ✗ Hybrid es {abs(improvement):.1%} MENOS RELEVANTE")
            print(f"│   Problemas potenciales en reranker - diagnosticar")
        
        print("└")
    
    def _analyze_performance(self, results):
        """Analyze performance metrics"""
        print("\n┌─ ANÁLISIS DE RENDIMIENTO")
        print("│")
        
        bm25_time = results['bm25']['avg_time_ms']
        hybrid_time = results['hybrid']['avg_time_ms']
        time_increase = results['improvement']['time_overhead_pct']
        
        print(f"│ BM25 Tiempo Promedio:   {bm25_time:.1f}ms")
        print(f"│ Hybrid Tiempo Promedio: {hybrid_time:.1f}ms")
        print(f"│ Overhead:               {time_increase:+.1%}")
        print("│")
        
        if hybrid_time < 1000:  # Less than 1 second
            print(f"│ ✓ Tiempo de respuesta ACEPTABLE (<1s)")
            print(f"│   Híbrida agrega {hybrid_time - bm25_time:.1f}ms")
        elif hybrid_time < 3000:  # Less than 3 seconds
            print(f"│ ⚠ Tiempo de respuesta MODERADO (1-3s)")
            print(f"│   Considere optimizar reranker o desactivar")
        else:
            print(f"│ ✗ Tiempo de respuesta INACEPTABLE (>3s)")
            print(f"│   RECOMENDACIÓN: No usar Hybrid sin optimización")
        
        print("└")
    
    def _analyze_trade_offs(self, results):
        """Analyze quality vs performance tradeoffs"""
        print("\n┌─ ANÁLISIS DE TRADE-OFFS")
        print("│")
        
        bm25_rel = results['bm25']['avg_relevance']
        hybrid_rel = results['hybrid']['avg_relevance']
        rel_improvement = (hybrid_rel - bm25_rel) / bm25_rel if bm25_rel > 0 else 0
        
        bm25_time = results['bm25']['avg_time_ms']
        hybrid_time = results['hybrid']['avg_time_ms']
        time_increase = (hybrid_time - bm25_time) / bm25_time if bm25_time > 0 else 0
        
        # Calculate quality/time ratio
        if hybrid_time > 0:
            bm25_quality_per_ms = bm25_rel / bm25_time if bm25_time > 0 else 0
            hybrid_quality_per_ms = hybrid_rel / hybrid_time
            
            efficiency_change = (hybrid_quality_per_ms - bm25_quality_per_ms) / bm25_quality_per_ms if bm25_quality_per_ms > 0 else 0
            
            print(f"│ BM25 Quality/Time:   {bm25_quality_per_ms:.6f}")
            print(f"│ Hybrid Quality/Time: {hybrid_quality_per_ms:.6f}")
            print(f"│ Eficiencia:          {efficiency_change:+.1%}")
            print("│")
            
            if efficiency_change > 0:
                print(f"│ ✓ Hybrid es MÁS EFICIENTE")
                print(f"│   Mejor calidad con costo menor")
            else:
                print(f"│ ✗ Hybrid es MENOS EFICIENTE")
                print(f"│   Requiere más tiempo para mejoría")
        
        print("└")
    
    def _generate_recommendations(self, results):
        """Generate recommendations for production deployment"""
        print("\n┌─ RECOMENDACIONES PARA PRODUCCIÓN")
        print("│")
        
        bm25_rel = results['bm25']['avg_relevance']
        hybrid_rel = results['hybrid']['avg_relevance']
        improvement = (hybrid_rel - bm25_rel) / bm25_rel if bm25_rel > 0 else 0
        
        hybrid_time = results['hybrid']['avg_time_ms']
        
        recommendations = []
        
        # Relevance-based
        if improvement > 0.2 and hybrid_time < 1000:
            recommendations.append("1. ACTIVAR HYBRID EN PRODUCCIÓN")
            recommendations.append("   - Mejora de relevancia >20%")
            recommendations.append("   - Tiempo aceptable <1s")
        elif improvement > 0.1 and hybrid_time < 2000:
            recommendations.append("1. ACTIVAR HYBRID CON MONITOREO")
            recommendations.append("   - Mejora moderada de relevancia")
            recommendations.append("   - Monitorear tiempo de respuesta")
        elif improvement > 0 and hybrid_time < 3000:
            recommendations.append("1. ACTIVAR HYBRID EN MODO BETA")
            recommendations.append("   - Solo para usuarios selectos")
            recommendations.append("   - Recolectar feedback")
        else:
            recommendations.append("1. MANTENER BM25 COMO BASELINE")
            recommendations.append("   - Optimizar configuración de Hybrid")
            recommendations.append("   - Investigar problema de reranker")
        
        # Performance-based
        if hybrid_time < 500:
            recommendations.append("2. RENDIMIENTO EXCELENTE")
            recommendations.append("   - Puede manejar tráfico alto")
        elif hybrid_time < 1000:
            recommendations.append("2. RENDIMIENTO BUENO")
            recommendations.append("   - Aceptable para mayoría de casos")
        elif hybrid_time < 3000:
            recommendations.append("2. RENDIMIENTO ACEPTABLE")
            recommendations.append("   - Considere caché o optimización")
        else:
            recommendations.append("2. RENDIMIENTO POBRE")
            recommendations.append("   - Requiere optimización antes de producción")
        
        # Language support
        recommendations.append("3. SOPORTE MULTIIDIOMA")
        recommendations.append("   - Verificar rendimiento por idioma")
        recommendations.append("   - Ajustar modelos de reranker si es necesario")
        
        # Monitoring
        recommendations.append("4. MONITOREO EN PRODUCCIÓN")
        recommendations.append("   - Rastrear relevancia de resultados")
        recommendations.append("   - Monitorear latencia P95/P99")
        recommendations.append("   - Recolectar feedback de usuarios")
        
        for rec in recommendations:
            if rec.startswith("   "):
                print(f"│   {rec[3:]}")
            else:
                print(f"│")
                print(f"│ {rec}")
        
        print("│")
        print("└")
        
        # Final summary
        print("\n┌─ RESUMEN EJECUTIVO")
        print("│")
        
        if improvement > 0 and hybrid_time < 2000:
            status = "✓ LISTO PARA EVALUAR EN PRODUCCIÓN"
            icon = "🟢"
        elif improvement > 0:
            status = "⏳ NECESITA OPTIMIZACIÓN"
            icon = "🟡"
        else:
            status = "❌ NO RECOMENDADO ACTUALMENTE"
            icon = "🔴"
        
        print(f"│ Estado: {status}")
        print(f"│")
        print(f"│ Próximos pasos:")
        print(f"│ 1. Ejecutar pruebas A/B en usuario real")
        print(f"│ 2. Recolectar feedback de relevancia")
        print(f"│ 3. Ajustar pesos de fusión si es necesario")
        print(f"│ 4. Implementar caché si latencia es alta")
        print(f"│ 5. Monitorear en producción")
        print("│")
        print("└")


def main():
    """Run analysis"""
    analyzer = ResultsAnalyzer()
    analyzer.analyze()


if __name__ == "__main__":
    main()
