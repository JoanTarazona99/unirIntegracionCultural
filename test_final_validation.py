#!/usr/bin/env python3
"""
Final Validation Test - 16 Questions on Improved KB
Tests pricing, admissions, deadlines, documents, visas, and scholarships
"""

import asyncio
import sys
import os
import json
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set UTF-8 output encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_questions():
    """Run 16-question test suite"""
    
    # Import after path setup
    from backend.app.api.models import QueryRequest
    from backend.app.api.dependencies import get_rag_service
    
    # Get RAG service
    rag_service = get_rag_service()
    
    # Test questions organized by category
    test_categories = {
        'COSTOS Y PAGOS': [
            '¿Cuál es el costo total de la matrícula para estudiantes internacionales?',
            '¿El precio varía si soy ciudadano de la Unión Europea o de fuera de ella?',
            '¿Cuáles son los plazos de pago y existe la opción de pagar en cuotas?',
            '¿Qué métodos de pago acepta la universidad desde el extranjero?',
        ],
        'REQUISITOS ACADÉMICOS Y DOCUMENTOS': [
            '¿Cómo y dónde debo legalizar o apostillar mis títulos académicos anteriores?',
            '¿Necesito traducir oficialmente mis documentos al idioma local?',
            '¿Qué exámenes de certificación de idioma (como TOEFL, IELTS o DELE) aceptan?',
            '¿Cuál es la nota mínima de admisión requerida para mi carrera?',
        ],
        'FECHAS LÍMITE Y PROCESO': [
            '¿Cuándo se abren y se cierran las convocatorias de inscripción para extranjeros?',
            '¿Puedo realizar todo el proceso de matrícula en línea o debo ir presencialmente?',
            '¿Cuánto tiempo tarda la universidad en emitir la carta de aceptación oficial?',
        ],
        'VISAS Y REQUISITOS LEGALES': [
            '¿Qué documentos me da la universidad para tramitar mi visa de estudiante?',
            '¿Necesito contratar un seguro médico específico para matricularme?',
            '¿La universidad exige una prueba de fondos económicos suficientes para aceptar la matrícula?',
        ],
        'BECAS Y AYUDAS': [
            '¿Los estudiantes extranjeros tienen acceso a becas de matrícula de la universidad?',
            '¿Existe algún descuento por excelencia académica aplicable a internacionales?',
        ]
    }
    
    print('\n' + '='*80)
    print('KNOWLEDGE INTEGRATION - FINAL VALIDATION TEST')
    print('='*80)
    
    results = {
        'total': 0,
        'llm': 0,
        'abstained': 0,
        'web_enhanced': 0,
        'avg_latency': 0,
        'avg_sources': 0,
        'questions': []
    }
    
    total_latency = 0
    total_sources = 0
    
    for category, questions in test_categories.items():
        print(f'\n{category}')
        print('-' * 80)
        
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
                answer = rag_result.get('response', '')[:100]
                mode = rag_result.get('response_mode', 'unknown')
                sources = rag_result.get('sources_found', 0)
                
                # Record results
                results['total'] += 1
                total_latency += latency
                total_sources += sources
                
                if mode == 'llm':
                    results['llm'] += 1
                elif mode == 'abstained':
                    results['abstained'] += 1
                elif 'web' in mode:
                    results['web_enhanced'] += 1
                
                results['questions'].append({
                    'question': question,
                    'mode': mode,
                    'sources': sources,
                    'latency': latency
                })
                
                # Print result
                print(f'[{i}] {question[:60]}...')
                print(f'    Answer: {answer}...')
                print(f'    Mode: {mode} | Sources: {sources} | Time: {latency:.1f}ms')
                print()
                
            except Exception as e:
                print(f'[{i}] ERROR: {str(e)}\n')
                results['total'] += 1
    
    # Calculate averages
    if results['total'] > 0:
        results['avg_latency'] = total_latency / results['total']
        results['avg_sources'] = total_sources / results['total']
    
    # Print summary
    print('='*80)
    print('SUMMARY')
    print('='*80)
    print(f'Total questions: {results["total"]}')
    print(f'LLM mode: {results["llm"]} ({100*results["llm"]/results["total"]:.0f}%)')
    print(f'Abstained: {results["abstained"]} ({100*results["abstained"]/results["total"]:.0f}%)')
    print(f'Web enhanced: {results["web_enhanced"]} ({100*results["web_enhanced"]/results["total"]:.0f}%)')
    print(f'Average latency: {results["avg_latency"]:.1f}ms')
    print(f'Average sources: {results["avg_sources"]:.1f}')
    print('='*80 + '\n')
    
    return results


if __name__ == '__main__':
    try:
        asyncio.run(test_questions())
    except Exception as e:
        print(f'Test failed: {e}')
        import traceback
        traceback.print_exc()
