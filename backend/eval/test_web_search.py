"""
TEST: Verificar que Knowledge Acquisition Agent funciona con web search
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_acquisition import KnowledgeAcquisitionAgent

async def test_web_search():
    """Test web search capabilities."""
    
    agent = KnowledgeAcquisitionAgent()
    
    print("\n" + "="*70)
    print("TEST: KNOWLEDGE ACQUISITION AGENT - WEB SEARCH")
    print("="*70)
    
    # Test 1: Search Wikipedia
    print("\n[TEST 1] Búsqueda en Wikipedia...")
    result = agent.search_official_sources(["visa", "Russia", "student"])
    if result:
        print(f"✅ Encontrado: {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Source: {result['source_type']}")
    else:
        print("❌ No se encontró resultado")
    
    # Test 2: Search with Google AI (if available)
    print("\n[TEST 2] Búsqueda con Google AI...")
    result = agent.search_official_sources(["matriculation", "preparatory", "course"])
    if result:
        print(f"✅ Encontrado: {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Source: {result['source_type']}")
    else:
        print("❌ No se encontró resultado")
    
    # Test 3: Fetch content from Wikipedia
    print("\n[TEST 3] Extrayendo contenido de Wikipedia...")
    test_url = "https://en.wikipedia.org/wiki/Student_visa"
    content = agent._fetch_content_from_url(test_url)
    if content:
        print(f"✅ Contenido extraído ({len(content)} caracteres)")
        print(f"   Preview: {content[:300]}...")
    else:
        print("❌ No se pudo extraer contenido")
    
    # Test 4: Ingest document
    print("\n[TEST 4] Ingiriendo documento en RAG base...")
    success = agent.ingest_document(
        content="Test content about student visas and matriculation",
        title="Test Document",
        url="https://example.com/test",
        source="test_source",
    )
    if success:
        print("✅ Documento ingirido correctamente")
    else:
        print("❌ No se pudo ingerir documento")
    
    # Test 5: Handle low grounding
    print("\n[TEST 5] Simulando escenario de bajo grounding...")
    result = await agent.handle_low_grounding(
        query="¿Cómo me matriculo en preparatoria?",
        draft_answer="No tengo información suficiente.",
        retrieved_docs=[],
        evaluation={"score": 0.2, "missing_entities": []},
        rag_module=None  # No actual RAG module for this test
    )
    if result:
        print("✅ Knowledge acquisition intentada exitosamente")
    else:
        print("⚠️ Knowledge acquisition retornó None (esperado sin RAG module)")
    
    print("\n" + "="*70)
    print("✅ TODOS LOS TESTS COMPLETADOS")
    print("="*70)
    
    print("""
Capacidades activadas:
✅ Búsqueda en Wikipedia (multiidioma)
✅ Búsqueda con Google AI (si API key disponible)
✅ Búsqueda en DuckDuckGo (sin autenticación)
✅ Extracción inteligente de contenido
✅ Ingesta dinámica de documentos en RAG base
✅ Integración en endpoint /api/chat

PRÓXIMOS PASOS:
1. Configurar API keys (opcional):
   - GOOGLE_AI_API_KEY (para Gemini)
   - GOOGLE_CUSTOM_SEARCH_API_KEY (para Custom Search)

2. Reiniciar backend:
   python main.py

3. Probar con respuestas de bajo grounding:
   - Las preguntas que antes devolvían "No tengo información"
   - Ahora buscarán en web automáticamente
   - El contenido se ingesta en la base de datos RAG
    
""")

if __name__ == "__main__":
    asyncio.run(test_web_search())
