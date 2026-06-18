#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demostración del módulo RAG mejorado
Busca en documentos oficiales: КубГУ, МВД РФ, МФЦ, Госуслуги
"""

from enhanced_rag import EnhancedRAGModule
import json
import sys

# Configurar encoding UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def demo_rag():
    print("="*70)
    print("[RAG] DEMOSTRACION DEL MODULO RAG MEJORADO")
    print("Documentos Oficiales: KubGU, MVD, MFC, Gosuslugi")
    print("="*70)
    
    # Inicializar RAG
    rag = EnhancedRAGModule()
    
    # Obtener lista de fuentes
    print("\n📚 FUENTES DISPONIBLES:")
    sources = rag.document_library.list_sources()
    for i, source in enumerate(sources, 1):
        print(f"  {i}. {source}")
    
    # Pruebas de búsqueda
    test_queries = [
        "Как зарегистрироваться?",
        "Общежитие",
        "Медицинская страховка",
        "Виза студента",
        "МФЦ услуги",
        "Права иностранного студента"
    ]
    
    print("\n" + "="*70)
    print("🔎 PRUEBAS DE BÚSQUEDA:")
    print("="*70)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}] Búsqueda: {query}")
        print("-" * 70)
        
        result = rag.search_and_generate(query)
        
        print(f"Resultados encontrados: {result['sources_found']}")
        if result['sources']:
            print(f"Fuente principal: {result['sources'][0]['source']}")
            print()
            print(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
    
    # Demostración personalizada
    print("\n" + "="*70)
    print("👤 RECOMENDACIONES PERSONALIZADAS POR PERFIL")
    print("="*70)
    
    user_profile = {
        'country': 'Vietnam',
        'visa_type': 'student',
        'academic_level': 'bachelor'
    }
    
    print(f"\nPerfil: Estudiante de {user_profile['country']}")
    recommendations = rag.get_recommendation(user_profile)
    
    for i, rec in enumerate(recommendations['recommendations'], 1):
        print(f"\n[Recomendación {i}]")
        print(f"Búsqueda: {rec['query']}")
        print(f"Respuesta: {rec['response'][:300]}...")
    
    # Exportar base de datos
    print("\n" + "="*70)
    print("💾 Exportando base de datos...")
    output_path = Path(__file__).parent.parent / "data" / "rag_database.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rag.export_to_json(output_path)
    print(f"✅ Exportado a: {output_path}")
    
    print("\n" + "="*70)
    print("✅ DEMOSTRACIÓN COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    from pathlib import Path
    demo_rag()
