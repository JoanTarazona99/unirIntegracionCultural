#!/usr/bin/env python3
"""
Advanced Test Suite - 16 Domain-Specific Questions
Tests legal procedures, accommodation, finance, daily life
Verifies auto-integration system effectiveness
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set UTF-8 output encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_advanced_questions():
    """Run 16 advanced domain-specific questions"""
    
    # Import after path setup
    from backend.app.api.models import QueryRequest
    from backend.app.api.dependencies import get_rag_service
    
    # Get RAG service
    rag_service = get_rag_service()
    
    # Test questions organized by domain
    test_domains = {
        'Trámites Legales y Migración': [
            '¿Dónde y en qué plazo debo realizar mi registro migratorio (registratsiya) al llegar?',
            '¿Qué documentos debo presentar en la oficina de relaciones internacionales de la universidad el primer día?',
            '¿Cómo y cuándo debo pasar los exámenes médicos obligatorios y la toma de huellas dactilares (daktiloskopiya)?',
            '¿Dónde puedo renovar mi visa de estudiante antes de que venza la de entrada?',
        ],
        'Alojamiento y Llegada': [
            '¿Cómo llego desde el aeropuerto (si está operativo) o la estación de tren (Krasnodar-1) hasta mi residencia universitaria o apartamento?',
            '¿Qué normas específicas tienen las residencias (obshchezhitie) de la universidad (horarios de cierre, visitas, cocina)?',
            '¿Si decido rentar un apartamento fuera del campus, el dueño está obligado a registrarme legalmente?',
        ],
        'Dinero, Conectividad y Transporte': [
            '¿Cómo puedo abrir una cuenta bancaria local (como Sberbank o Tinkoff) siendo extranjero?',
            '¿Qué opciones tengo para transferir dinero desde mi país de origen dadas las restricciones financieras actuales?',
            '¿Dónde puedo comprar una tarjeta SIM local (MTS, MegaFon, Beeline) solo con mi pasaporte?',
            '¿Cómo funciona la tarjeta de transporte público en Krasnodar y cómo pido un taxi seguro (Yandex Go)?',
        ],
        'Vida Diaria y Clima': [
            '¿Dónde están los supermercados más económicos (Magnit o Pyaterochka) cerca de la zona universitaria?',
            'El clima de Krasnodar es muy caluroso en verano pero frío en invierno, ¿dónde puedo comprar ropa de invierno adecuada a buen precio?',
            '¿Cómo accedo a los servicios médicos de la universidad o qué hospital me corresponde con mi seguro médico para extranjeros?',
        ]
    }
    
    print('\n' + '='*90)
    print('ADVANCED QUESTION TEST SUITE - LEGAL, ACCOMMODATION, FINANCE, DAILY LIFE')
    print('='*90)
    
    results = {
        'total': 0,
        'llm': 0,
        'abstained': 0,
        'web_enhanced': 0,
        'avg_latency': 0,
        'avg_sources': 0,
        'domains': {},
        'questions': []
    }
    
    total_latency = 0
    total_sources = 0
    
    for domain, questions in test_domains.items():
        print(f'\n{domain}')
        print('-' * 90)
        
        domain_results = {'llm': 0, 'abstained': 0, 'web': 0, 'count': 0}
        
        for i, question in enumerate(questions, 1):
            try:
                t_start = time.perf_counter()
                
                # Make request
                rag_result = rag_service.search(
                    query=question,
                    language='es',
                    context_type='chat_es'
                )
                
                t_end = time.perf_counter()
                latency = (t_end - t_start) * 1000
                
                # Extract metrics
                answer = rag_result.get('response', '')[:120]
                mode = rag_result.get('response_mode', 'unknown')
                sources = rag_result.get('sources_found', 0)
                grounding = rag_result.get('grounding_score', 0)
                
                # Record results
                results['total'] += 1
                domain_results['count'] += 1
                total_latency += latency
                total_sources += sources
                
                if mode == 'llm':
                    results['llm'] += 1
                    domain_results['llm'] += 1
                elif mode == 'abstained':
                    results['abstained'] += 1
                    domain_results['abstained'] += 1
                elif 'web' in mode:
                    results['web_enhanced'] += 1
                    domain_results['web'] += 1
                
                results['questions'].append({
                    'domain': domain,
                    'question': question,
                    'mode': mode,
                    'sources': sources,
                    'grounding': grounding,
                    'latency': latency
                })
                
                # Print result
                status = '✓' if mode == 'llm' else ('⚠' if mode == 'abstained' else '🌐')
                print(f'{status} [{i}] {question[:70]}...')
                print(f'   Mode: {mode} | Sources: {sources} | Grounding: {grounding:.2f} | Time: {latency:.0f}ms')
                
                # Show answer preview
                print(f'   Answer: {answer}...\n')
                
            except Exception as e:
                print(f'✗ [{i}] ERROR: {str(e)}\n')
                results['total'] += 1
                domain_results['count'] += 1
        
        results['domains'][domain] = domain_results
    
    # Calculate averages
    if results['total'] > 0:
        results['avg_latency'] = total_latency / results['total']
        results['avg_sources'] = total_sources / results['total']
    
    # Print summary by domain
    print('\n' + '='*90)
    print('DOMAIN SUMMARY')
    print('='*90)
    for domain, metrics in results['domains'].items():
        if metrics['count'] > 0:
            llm_pct = 100 * metrics['llm'] / metrics['count']
            abs_pct = 100 * metrics['abstained'] / metrics['count']
            web_pct = 100 * metrics['web'] / metrics['count']
            print(f'{domain:40s} | LLM: {metrics["llm"]}/{metrics["count"]} ({llm_pct:.0f}%) | Abstained: {metrics["abstained"]} ({abs_pct:.0f}%) | Web: {metrics["web"]} ({web_pct:.0f}%)')
    
    # Print overall summary
    print('\n' + '='*90)
    print('OVERALL SUMMARY')
    print('='*90)
    print(f'Total questions: {results["total"]}')
    print(f'LLM mode: {results["llm"]} ({100*results["llm"]/results["total"]:.0f}%)')
    print(f'Abstained: {results["abstained"]} ({100*results["abstained"]/results["total"]:.0f}%)')
    print(f'Web enhanced: {results["web_enhanced"]} ({100*results["web_enhanced"]/results["total"]:.0f}%)')
    print(f'Average latency: {results["avg_latency"]:.0f}ms')
    print(f'Average sources: {results["avg_sources"]:.1f}')
    print('='*90 + '\n')
    
    # Check integration status
    print('\n' + '='*90)
    print('CHECKING AUTO-INTEGRATION STATUS')
    print('='*90)
    
    from backend.knowledge_integrator import KnowledgeIntegrator
    integrator = KnowledgeIntegrator()
    status = integrator.get_integration_status()
    
    print(f'Total acquisitions: {status["total_acquisitions"]}')
    print(f'Successful acquisitions: {status["successful_acquisitions"]}')
    print(f'Already integrated: {status["integrated_count"]}')
    print(f'Pending integrations: {status["pending_count"]}')
    
    if status['pending_count'] > 0:
        print(f'\nPENDING QUERIES FOR AUTO-INTEGRATION:')
        for query in status['pending_queries'][:5]:
            print(f'  - {query}')
    
    print('='*90 + '\n')
    
    return results


if __name__ == '__main__':
    try:
        asyncio.run(test_advanced_questions())
    except Exception as e:
        print(f'Test failed: {e}')
        import traceback
        traceback.print_exc()
