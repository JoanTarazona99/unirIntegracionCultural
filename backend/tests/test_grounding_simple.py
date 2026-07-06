"""
Tests simplificados para evaluador de fidelidad mejorado y citation_guard.
SIN dependencias de transformers/sentence-transformers (evita error PyTorch 3.13).

Valida logica pura: entity extraction, hard matching, multi-level grounding, policy.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import only what we need (no transformers)
from trust.hallucination import (
    _extract_numbers,
    _extract_dates,
    _extract_currency_amounts,
    _extract_domain_terms,
    _extract_time_durations,
    _hard_match_entities,
    estimate_faithfulness,
    analyze_grounding_improved,
    GroundingLevel,
)
from trust.citation import (
    _is_sensitive_topic,
    enforce_grounding_improved,
    format_citations,
)


def test_extract_numbers():
    """Test number extraction."""
    print("\n[TEST] Extraccion de numeros")
    text = "El curso cuesta 50,000 rublos o 100-150 USD. Dura 3-6 meses."
    numbers = _extract_numbers(text)
    print(f"   Texto: {text}")
    print(f"   Numeros encontrados: {numbers}")
    assert len(numbers) > 0
    assert any("50" in n for n in numbers)
    print("   [OK] PASS")


def test_extract_dates():
    """Test date extraction."""
    print("\n[TEST] Extraccion de fechas")
    text = "Registro antes de 15.03.2024. Curso comienza 15 enero 2024."
    dates = _extract_dates(text)
    print(f"   Texto: {text}")
    print(f"   Fechas encontradas: {dates}")
    assert len(dates) > 0
    print("   [OK] PASS")


def test_extract_currency():
    """Test currency extraction."""
    print("\n[TEST] Extraccion de moneda")
    text = "Cuesta $5000 o 100,000 rublos. Tuicion: 2000 EUR."
    amounts = _extract_currency_amounts(text)
    print(f"   Texto: {text}")
    print(f"   Monedas encontradas: {amounts}")
    assert len(amounts) > 0
    print("   [OK] PASS")


def test_extract_domain_terms():
    """Test domain term extraction."""
    print("\n[TEST] Extraccion de terminos de dominio")
    text = "Para visa de estudiante y registro en KubGU, necesitas certificado TRKI."
    terms = _extract_domain_terms(text)
    print(f"   Texto: {text}")
    print(f"   Terminos encontrados: {terms}")
    assert "visa" in terms or "visado" in terms
    print("   [OK] PASS")


def test_extract_durations():
    """Test duration extraction."""
    print("\n[TEST] Extraccion de duraciones")
    text = "El curso dura 3 meses, 6 semanas, o 2 anos."
    durations = _extract_time_durations(text)
    print(f"   Texto: {text}")
    print(f"   Duraciones encontradas: {durations}")
    assert len(durations) > 0
    print("   [OK] PASS")


def test_case_high_fidelity():
    """CASE 1: Well-supported answer."""
    print("\n[TEST] CASO 1: Respuesta bien soportada")
    context = [
        "El curso preparatorio de ruso dura 3-6 meses.",
        "El costo es aproximadamente 50,000-100,000 rublos.",
    ]
    answer = "El curso preparatorio dura 3 a 6 meses y cuesta entre 50,000 y 100,000 rublos."
    
    hard_score, matched, missing = _hard_match_entities(answer, context)
    print(f"   Hard score: {hard_score}")
    print(f"   Matched: {matched}")
    print(f"   Missing: {missing}")
    assert hard_score > 0.6
    assert len(matched) > 0
    print("   [OK] PASS")


def test_case_medium_fidelity():
    """CASE 2: Partial support."""
    print("\n[TEST] CASO 2: Respuesta con soporte parcial")
    context = [
        "KubGU esta ubicada en Krasnodar.",
        "Ofrece programas en ruso e ingles.",
    ]
    answer = "KubGU esta en Krasnodar y ofrece cursos de ruso. La matricula cuesta aproximadamente 100,000 rublos."
    
    hard_score, matched, missing = _hard_match_entities(answer, context)
    print(f"   Hard score: {hard_score}")
    print(f"   Matched: {len(matched)} entities")
    print(f"   Missing: {missing}")
    assert len(missing) > 0
    print("   [OK] PASS")


def test_case_low_fidelity():
    """CASE 3: Unsupported answer."""
    print("\n[TEST] CASO 3: Respuesta sin soporte")
    context = [
        "La visa de estudiante requiere un certificado de nivel B1 de ruso.",
    ]
    answer = "Para obtener la visa de estudiante en KubGU, necesitas un nivel C1 de ruso, certificado por TRKI, y pagar 200,000 rublos por semestre."
    
    analysis = analyze_grounding_improved(answer, context)
    print(f"   Score: {analysis.score}")
    print(f"   Level: {analysis.level.value}")
    print(f"   Missing: {analysis.missing_entities}")
    assert analysis.level == GroundingLevel.LOW
    print("   [OK] PASS")


def test_no_entities():
    """CASE 4: Response with no numbers."""
    print("\n[TEST] CASO 4: Respuesta sin numeros (solo lexical)")
    context = ["KubGU es una buena universidad en Rusia."]
    answer = "KubGU es una institucion educativa de calidad ubicada en Rusia."
    
    analysis = analyze_grounding_improved(answer, context)
    print(f"   Score: {analysis.score}")
    assert 0 <= analysis.score <= 1
    print("   [OK] PASS")


def test_grounding_high():
    """Test HIGH grounding level."""
    print("\n[TEST] Analisis de grounding - Nivel HIGH")
    context = [
        "El curso dura 3-6 meses y cuesta 50,000-100,000 rublos.",
        "Se ofrece en KubGU todo el ano.",
    ]
    answer = "El curso dura 3 a 6 meses y cuesta entre 50,000 y 100,000 rublos, ofrecido en KubGU."
    
    analysis = analyze_grounding_improved(answer, context)
    print(f"   Score: {analysis.score}")
    print(f"   Level: {analysis.level.value}")
    assert analysis.level == GroundingLevel.HIGH
    print("   [OK] PASS")


def test_grounding_medium():
    """Test MEDIUM grounding level."""
    print("\n[TEST] Analisis de grounding - Nivel MEDIUM")
    context = ["KubGU esta en Krasnodar."]
    answer = "KubGU es una universidad en Krasnodar que ofrece cursos especiales."
    
    analysis = analyze_grounding_improved(answer, context)
    print(f"   Score: {analysis.score}")
    print(f"   Level: {analysis.level.value}")
    assert analysis.level in [GroundingLevel.MEDIUM, GroundingLevel.LOW]
    print("   [OK] PASS")


def test_grounding_low():
    """Test LOW grounding level."""
    print("\n[TEST] Analisis de grounding - Nivel LOW")
    context = ["Informacion general sobre visados."]
    answer = "Necesitas nivel C1 de ruso para la visa, certificado TRKI, y pagar 500,000 rublos por semestre en KubGU."
    
    analysis = analyze_grounding_improved(answer, context)
    print(f"   Score: {analysis.score}")
    print(f"   Level: {analysis.level.value}")
    assert analysis.level == GroundingLevel.LOW, f"Esperaba LOW pero obtuve {analysis.level.value}"
    print("   [OK] PASS")


def test_lexical_faithfulness():
    """Test lexical faithfulness score."""
    print("\n[TEST] Fidelidad lexical (original)")
    answer = "El curso dura 3 meses y cuesta 50,000 rublos."
    contexts = ["El curso preparatorio dura 3 meses. Cuesta aproximadamente 50,000 rublos."]
    
    lexical_score = estimate_faithfulness(answer, contexts)
    print(f"   Lexical score: {lexical_score}")
    assert 0 <= lexical_score <= 1
    print("   [OK] PASS")


def test_sensitive_topics():
    """Test sensitive topic detection."""
    print("\n[TEST] Deteccion de temas sensibles")
    queries = [
        "How do I get a visa?",
        "Cual es la tarifa de matricula?",
        "Kak poluchit vizhu?",
    ]
    
    results = [_is_sensitive_topic(q) for q in queries]
    print(f"   Queries: {len(queries)}")
    print(f"   Sensitive detected: {sum(results)}")
    assert sum(results) >= 2
    print("   [OK] PASS")


def test_citation_guard_high():
    """Test citation guard HIGH level."""
    print("\n[TEST] Citation Guard - HIGH (responde normalmente)")
    answer = "El curso dura 3 a 6 meses."
    results = [{"source": "KubGU", "content": "El curso dura 3-6 meses."}]
    
    result = enforce_grounding_improved(answer, results)
    print(f"   Score: {result.score:.2f}")
    print(f"   Level: {result.level}")
    print(f"   Abstained: {result.abstained}")
    assert not result.abstained
    print("   [OK] PASS")


def test_citation_guard_low():
    """Test citation guard LOW level."""
    print("\n[TEST] Citation Guard - LOW (se abstiene)")
    answer = "El curso cuesta 500,000 rublos por semestre."
    results = [{"source": "KubGU", "content": "No hay informacion de precios."}]
    
    result = enforce_grounding_improved(answer, results)
    print(f"   Score: {result.score:.2f}")
    print(f"   Level: {result.level}")
    print(f"   Abstained: {result.abstained}")
    assert result.abstained
    print("   [OK] PASS")


def test_citation_guard_strict():
    """Test citation guard strict mode."""
    print("\n[TEST] Citation Guard - Modo estricto (visa)")
    answer = "Para la visa necesitas nivel B1 de ruso."
    results = [{"source": "MVD", "content": "Visa requiere certificado de ruso."}]
    
    result_normal = enforce_grounding_improved(answer, results, strict_mode=False)
    result_strict = enforce_grounding_improved(answer, results, strict_mode=True)
    
    print(f"   Normal - Score: {result_normal.score:.2f}, Level: {result_normal.level}")
    print(f"   Strict - Score: {result_strict.score:.2f}, Level: {result_strict.level}")
    print("   [OK] PASS")


def test_format_citations():
    """Test citation formatting."""
    print("\n[TEST] Formato de citaciones")
    results = [
        {"source": "KubGU", "source_url": "https://kubsu.ru", "title": "Universidad"},
        {"source": "KubGU", "source_url": "https://kubsu.ru", "title": "Universidad"},
        {"source": "MVD", "source_url": "https://mvd.ru", "title": "Migracion"},
        {"source": "MFC", "source_url": "https://mfc.ru", "title": "Servicios"},
    ]
    
    citations = format_citations(results, max_sources=3)
    print(f"   Input: {len(results)} resultados")
    print(f"   Output: {len(citations)} citaciones")
    for c in citations:
        print(f"     - {c['source']}: {c['url']}")
    
    assert len(citations) <= 3
    assert len(set(c['source'] for c in citations)) == len(citations)
    print("   [OK] PASS")


def run_all_tests():
    """Run all tests."""
    tests = [
        test_extract_numbers,
        test_extract_dates,
        test_extract_currency,
        test_extract_domain_terms,
        test_extract_durations,
        test_case_high_fidelity,
        test_case_medium_fidelity,
        test_case_low_fidelity,
        test_no_entities,
        test_grounding_high,
        test_grounding_medium,
        test_grounding_low,
        test_lexical_faithfulness,
        test_sensitive_topics,
        test_citation_guard_high,
        test_citation_guard_low,
        test_citation_guard_strict,
        test_format_citations,
    ]
    
    print("\n" + "=" * 70)
    print("TESTS DE GROUNDING MEJORADO (SIN TRANSFORMERS)")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"   [FAIL]: {e}")
    
    print("\n" + "=" * 70)
    print("RESULTS: {} PASS, {} FAIL".format(passed, failed))
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
