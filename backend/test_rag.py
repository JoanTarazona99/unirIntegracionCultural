#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demostracion del modulo RAG mejorado
Busca en documentos oficiales: КубГУ, МВД РФ, МФЦ, Госуслуги
"""

from enhanced_rag import EnhancedRAGModule
from pathlib import Path
import json
import sys

# Configurar encoding para Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    print("="*70)
    print("[RAG] MODULO MEJORADO DE BUSQUEDA - DOCUMENTOS OFICIALES")
    print("="*70)
    
    rag = EnhancedRAGModule()
    
    print("\n[FUENTES] Disponibles:")
    sources = rag.document_library.list_sources()
    for i, source in enumerate(sources, 1):
        print(f"  {i}. {source}")
    
    test_queries = [
        "registrarse lugar de residencia",
        "Comun dormitorio",
        "Seguro medico",
        "Visa estudiante"
    ]
    
    print("\n" + "="*70)
    print("[BUSQUEDAS] Pruebas de busqueda:")
    print("="*70)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}] Query: {query}")
        print("-" * 70)
        
        result = rag.search_and_generate(query)
        print(f"Resultados encontrados: {result['sources_found']}")
        
        if result['sources']:
            print(f"Fuente: {result['sources'][0]['source']}")
            response_preview = result['response'][:400]
            print(response_preview + ("..." if len(result['response']) > 400 else ""))
    
    print("\n" + "="*70)
    print("[EXPORT] Generando base de datos JSON...")
    output_path = Path(__file__).parent.parent / "data" / "rag_database.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rag.export_to_json(output_path)
    print(f"[OK] Archivo guardado: {output_path}")
    
    print("\n" + "="*70)
    print("[OK] MODULO RAG MEJORADO - OPERACIONAL")
    print("="*70)


if __name__ == "__main__":
    main()
