#!/usr/bin/env python3
"""Test web search fallback in RAG service (synchronous)"""

import sys
import time
sys.path.insert(0, 'backend')

from enhanced_rag import EnhancedRAGModule

print("=" * 80)
print("Testing web search fallback in RAG service")
print("=" * 80)

rag = EnhancedRAGModule()

# Test queries with expected low grounding
test_queries = [
    "¿Cómo llego desde el aeropuerto?",  # Expect low grounding, should trigger web search
    "¿Qué horarios tienen las residencias?",  # Expect low grounding, should trigger web search
]

for query in test_queries:
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}")
    
    start = time.time()
    result = rag.search_and_generate(
        query=query,
        context_type='chat_es',
        language='es',
        use_llm=True
    )
    elapsed = time.time() - start
    
    print(f"\nResult obtained in {elapsed:.1f}s")
    print(f"Response mode: {result.get('response_mode')}")
    print(f"Grounding score: {result.get('grounding_score'):.2f}")
    print(f"Sources: {result.get('sources_found')}")
    print(f"Response: {result.get('response', '')[:200]}...")
    
    if result.get('response_mode') == 'web_enhanced':
        print("\n✅ WEB SEARCH TRIGGERED!")
    else:
        print(f"\n⚠️  No web search (mode: {result.get('response_mode')})")

print("\n" + "=" * 80)
print("Test completed")
print("=" * 80)
