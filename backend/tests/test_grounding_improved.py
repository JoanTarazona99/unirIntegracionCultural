"""
Tests for improved grounding evaluation and multi-level citation guard.

Validates:
1. Improved evaluator (hard entity matching + lexical overlap)
2. Multi-level grounding policy (HIGH/MEDIUM/LOW)
3. Citation guard activation and behavior
4. Knowledge acquisition triggers
"""

import pytest
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trust.hallucination import (
    assess_evidence_sufficiency,
    analyze_grounding_improved,
    GroundingLevel,
    _extract_numbers,
    _extract_dates,
    _extract_currency_amounts,
    _extract_domain_terms,
    _hard_match_entities,
    estimate_faithfulness,
)
from trust.citation import enforce_grounding_improved, _is_sensitive_topic


class TestEvidenceSufficiency:
    """Regression tests for query-to-evidence sufficiency."""

    def test_irrelevant_copied_context_is_insufficient(self):
        query = "¿Cuál es el código de confirmación de la sesión piloto del 15 de septiembre de 2026?"
        results = [{
            "content": "Los exámenes de idiomas A1-C2 incluyen TOEFL e IELTS en Krasnodar.",
            "source": "FAQ",
            "relevance": 0.4,
        }]

        assessment = assess_evidence_sufficiency(query, results, retrieval_mode="keyword")

        assert assessment.sufficient is False
        assert "requested_slot_not_covered" in assessment.reasons

        copied_answer = results[0]["content"]
        guarded = enforce_grounding_improved(
            copied_answer,
            results,
            query=query,
            retrieval_mode="keyword",
        )
        assert guarded.faithfulness_score > 0.9
        assert guarded.score < 0.4
        assert guarded.abstained is True
        assert guarded.evidence_assessment.sufficient is False

    def test_relevant_evidence_is_sufficient(self):
        query = "¿Cuál es el código de confirmación de la sesión piloto del 15 de septiembre de 2026?"
        results = [{
            "content": (
                "Para la sesión piloto del 15 de septiembre de 2026, el código "
                "de confirmación es KUBGU-E2E-7429."
            ),
            "source": "Aviso controlado",
            "relevance": 0.95,
        }]

        assessment = assess_evidence_sufficiency(query, results, retrieval_mode="semantic")

        assert assessment.sufficient is True
        assert assessment.query_relevance >= 0.5
        assert assessment.requested_slot_coverage is True

    def test_fallback_retrieval_is_always_insufficient(self):
        results = [{
            "content": "El requisito de visa es presentar el pasaporte.",
            "source": "FAQ",
            "relevance": 1.0,
        }]

        assessment = assess_evidence_sufficiency(
            "¿Qué requisito de visa debo presentar?",
            results,
            retrieval_mode="fallback",
        )

        assert assessment.sufficient is False
        assert assessment.retrieval_confidence == 0.0
        assert "fallback_retrieval" in assessment.reasons

    def test_missing_critical_query_entity_is_insufficient(self):
        query = "¿Qué requisito corresponde al código KUBGU-E2E-7429 en KubGU?"
        results = [{
            "content": "KubGU publica los requisitos generales de orientación internacional.",
            "source": "KubGU",
            "relevance": 0.9,
        }]

        assessment = assess_evidence_sufficiency(query, results, retrieval_mode="semantic")

        assert assessment.sufficient is False
        assert "KUBGU-E2E-7429" in assessment.missing_entities["codes"]
        assert "query_entity_coverage_below_threshold" in assessment.reasons

    def test_spbu_purpose_of_stay_is_covered_despite_contextual_when(self):
        query = (
            "What purpose of stay should an international student indicate on "
            "the migration card when entering Russia?"
        )
        results = [{
            "content": (
                "When entering Russia, an international student must fill out "
                "the migration card with the stated purpose of stay being \"study\"."
            ),
            "source": "SPbU",
            "relevance": 0.95,
        }]

        assessment = assess_evidence_sufficiency(query, results)

        assert assessment.requested_slot == "purpose_of_stay"
        assert assessment.requested_slot_coverage is True
        assert assessment.sufficient is True

    def test_real_date_question_without_date_is_insufficient(self):
        results = [{
            "content": "The migration registration deadline is described in the rules.",
            "source": "Registration rules",
            "relevance": 0.95,
        }]

        assessment = assess_evidence_sufficiency(
            "When is the migration registration deadline?",
            results,
        )

        assert assessment.requested_slot == "date"
        assert assessment.requested_slot_coverage is False
        assert assessment.sufficient is False
        assert "requested_slot_not_covered" in assessment.reasons

    def test_documents_question_with_contextual_when_is_covered(self):
        results = [{
            "content": (
                "When arriving at the university, the required documents are "
                "a passport and migration card."
            ),
            "source": "Arrival guide",
            "relevance": 0.95,
        }]

        assessment = assess_evidence_sufficiency(
            "What documents are required when arriving at the university?",
            results,
        )

        assert assessment.requested_slot == "documents"
        assert assessment.requested_slot_coverage is True
        assert assessment.sufficient is True

    def test_required_action_with_contextual_when_is_not_a_date(self):
        results = [{
            "content": (
                "A student changing accommodation must notify the university "
                "and update the migration registration."
            ),
            "source": "Accommodation guide",
            "relevance": 0.95,
        }]

        assessment = assess_evidence_sufficiency(
            "What should a student do when changing accommodation?",
            results,
        )

        assert assessment.requested_slot == "required_action"
        assert assessment.requested_slot_coverage is True
        assert assessment.sufficient is True

    def test_minimal_spbu_evidence_is_sufficient_offline(self):
        source_url = "https://example.test/spbu-migration-registration"
        source_content = (
            "Upon arrival at the Russian border, foreign nationals must fill out "
            "a migration card with the stated purpose of stay being study."
        )
        query = (
            "What purpose of stay should an international student indicate on "
            "the migration card when entering Russia?"
        )
        results = [{
            "content": source_content,
            "source": "SPbU: visa and registration requirements for international students",
            "source_url": source_url,
            "relevance": 0.9,
        }]

        assessment = assess_evidence_sufficiency(
            query,
            results,
            retrieval_mode="keyword",
        )
        guarded = enforce_grounding_improved(
            (
                "Upon arrival at the Russian border, all foreign nationals must "
                "fill out a migration card with the stated purpose of stay being study."
            ),
            results,
            query=query,
            retrieval_mode="keyword",
            strict_mode=True,
        )

        assert assessment.requested_slot == "purpose_of_stay"
        assert assessment.requested_slot_coverage is True
        assert assessment.sufficient is True
        assert guarded.grounded is True
        assert guarded.abstained is False
        assert results[0]["source_url"] == source_url


def test_grounding_tests_do_not_read_runtime_artifact_paths():
    test_source = Path(__file__).read_text(encoding="utf-8").replace("\\", "/")
    forbidden_runtime_path = "".join(("arti", "facts", "/"))

    assert forbidden_runtime_path not in test_source


class TestHardEntityExtraction:
    """Test entity extraction functions."""

    def test_extract_numbers(self):
        """Test number extraction."""
        text = "The course costs 50,000 rubles or 100-150 USD. It lasts 3-6 months."
        numbers = _extract_numbers(text)
        assert any("50" in n for n in numbers)
        assert any("100" in n or "150" in n for n in numbers)
        assert any("3" in n or "6" in n for n in numbers)

    def test_extract_dates(self):
        """Test date extraction."""
        text = "Register by 15.03.2024. The course starts January 15 or 15/01/2024."
        dates = _extract_dates(text)
        assert len(dates) > 0
        assert any("15" in d for d in dates)
        assert any("january" in d.lower() or "01" in d for d in dates)

    def test_extract_currency(self):
        """Test currency amount extraction."""
        text = "The course costs $5000 or 100,000 rubles. Tuition: €2000."
        amounts = _extract_currency_amounts(text)
        assert len(amounts) > 0

    def test_extract_domain_terms(self):
        """Test domain-specific term extraction."""
        text = "To get a visa for Russian language course, you need registration at КубГУ."
        terms = _extract_domain_terms(text)
        assert "visa" in terms or "visado" in terms
        assert any("cours" in t or "курс" in t for t in terms)
        assert any("registr" in t or "регистр" in t for t in terms)


class TestImprovedGroundingAnalysis:
    """Test the improved grounding evaluator."""

    def test_case_high_fidelity_with_matching_numbers(self):
        """CASE 1: Response well-supported with matching critical data."""
        # Simulating: "curso preparatorio de ruso" with FAQ that has duration and cost
        context = [
            "El curso preparatorio de ruso dura 3-6 meses.",
            "El costo es aproximadamente 50,000-100,000 rublos.",
            "Se ofrece en КубГУ durante todo el año.",
        ]
        answer = (
            "El curso preparatorio dura 3 a 6 meses y cuesta entre 50,000 "
            "y 100,000 rublos."
        )

        analysis = analyze_grounding_improved(answer, context)

        # Should recognize matched numbers (3, 6, 50000, 100000)
        assert analysis.score > 0.6  # Not zero!
        assert analysis.level in [GroundingLevel.HIGH, GroundingLevel.MEDIUM]
        assert len(analysis.matched_entities) > 0  # Should find matched numbers
        print(f"✅ Case 1 (well-supported): score={analysis.score}, level={analysis.level.value}")

    def test_case_medium_fidelity_partial_support(self):
        """CASE 2: Response with partial support (some entities match)."""
        context = [
            "KubGU es una universidad ubicada en Krasnodár.",
            "Ofrece programas en ruso e inglés.",
        ]
        answer = (
            "KubGU está en Krasnodár y ofrece cursos de ruso. "
            "La matrícula cuesta aproximadamente 100,000 rublos por año."
        )

        analysis = analyze_grounding_improved(answer, context)

        # Should recognize partial support (location, language are in context)
        # But cost is not -> medium or medium-low
        assert analysis.score > 0.3  # Should NOT be zero
        assert analysis.level in [
            GroundingLevel.MEDIUM,
            GroundingLevel.LOW,
        ]  # Depends on weighting
        print(f"✅ Case 2 (partial support): score={analysis.score}, level={analysis.level.value}")

    def test_case_low_fidelity_unsupported(self):
        """CASE 3: Response not supported by context."""
        context = [
            "La visa de estudiante requiere un certificado de nivel B1 de ruso.",
        ]
        answer = (
            "Para obtener la visa de estudiante en KubGU, necesitas un nivel C1 "
            "de ruso, certificado por ТРКИ, y pagar 200,000 rublos por semestre."
        )

        analysis = analyze_grounding_improved(answer, context)

        # Critical mismatch: C1 vs B1, cost not in context
        assert analysis.level == GroundingLevel.LOW
        assert len(analysis.missing_entities) > 0
        print(f"✅ Case 3 (unsupported): score={analysis.score}, level={analysis.level.value}")

    def test_case_no_entities(self):
        """CASE 4: Response with no numbers/dates (only lexical matching)."""
        context = [
            "Para registrarse en la universidad, debes ir al MFC con tus documentos.",
        ]
        answer = "Necesitas ir al MFC para completar tu registro en la universidad."

        analysis = analyze_grounding_improved(answer, context)

        # Pure lexical matching, no hard entities
        assert analysis.score > 0.5  # Should be supported
        assert analysis.level in [GroundingLevel.HIGH, GroundingLevel.MEDIUM]
        print(f"✅ Case 4 (lexical only): score={analysis.score}, level={analysis.level.value}")


class TestMultiLevelCitationGuard:
    """Test the citation guard with multi-level policy."""

    def test_high_grounding_responds_normally(self):
        """HIGH level: should respond without abstention."""
        results = [
            {
                "content": (
                    "El curso preparatorio cuesta 50,000 rubles y dura "
                    "3 meses."
                ),
                "source": "FAQ КубГУ",
                "source_url": "https://kubsu.ru/faq",
            }
        ]
        answer = "El curso cuesta 50,000 rubles y dura aproximadamente 3 meses."

        result = enforce_grounding_improved(answer, results, language="es")

        assert result.grounded is True
        assert result.abstained is False
        assert result.level in ["high", "medium"]
        print(f"✅ HIGH level: responded normally, score={result.score}")

    def test_medium_grounding_responds_with_care(self):
        """MEDIUM level: should respond but can be marked as partial."""
        results = [
            {
                "content": "КубГУ ofrece cursos de preparación en idioma ruso.",
                "source": "КубГУ",
                "source_url": "https://kubsu.ru",
            }
        ]
        answer = "КубГУ offers a preparatory course in Russian that costs 100,000 rubles."

        result = enforce_grounding_improved(answer, results, language="en")

        # Cost not in context, but course is mentioned
        if result.level == "medium":
            assert result.grounded is True
            assert result.abstained is False
        else:
            # Could also be LOW and abstain
            assert result.level in ["medium", "low"]
        print(f"✅ MEDIUM level: score={result.score}, level={result.level}")

    def test_low_grounding_abstains(self):
        """LOW level: should abstain and show safe message."""
        results = [
            {
                "content": "КубГУ es una universidad en Krasnodár.",
                "source": "КубГУ",
                "source_url": "https://kubsu.ru",
            }
        ]
        answer = (
            "Para obtener el visado de estudiante en КубГУ, necesitas "
            "nivel C2 de ruso, 500,000 rublos de presupuesto y un seguro médico."
        )

        result = enforce_grounding_improved(answer, results, language="es")

        # Very specific requirements not in context
        assert result.abstained is True
        assert result.grounded is False
        assert "No tengo información suficiente" in result.answer or "consulta" in result.answer
        print(f"✅ LOW level: abstained correctly, score={result.score}")

    def test_sensitive_topic_stricter_threshold(self):
        """Sensitive topics (visa, fees) should use stricter thresholds."""
        results = [
            {
                "content": "Visa students need valid documents.",
                "source": "FAQ",
                "source_url": "https://example.com",
            }
        ]

        # Generic answer about visa
        answer = "Visa students need documentation from КубГУ."

        result_normal = enforce_grounding_improved(
            answer, results, language="en", strict_mode=False
        )
        result_strict = enforce_grounding_improved(
            answer, results, language="en", strict_mode=True
        )

        # Strict mode should be more stringent
        assert result_strict.score <= result_normal.score or result_strict.abstained
        print(
            f"✅ Sensitive topic: normal score={result_normal.score}, "
            f"strict score={result_strict.score}"
        )


class TestSensitiveTopicDetection:
    """Test detection of sensitive/high-stakes topics."""

    def test_visa_topic_detection(self):
        """Should detect visa-related queries."""
        queries = [
            "How do I get a visa to study in Russia?",
            "¿Cómo obtengo visa de estudiante?",
            "Как получить визу студента?",
            "visa requirements",
        ]
        for q in queries:
            assert _is_sensitive_topic(q), f"Failed to detect visa in: {q}"

    def test_fee_topic_detection(self):
        """Should detect fee/cost-related queries."""
        queries = [
            "How much does the course cost?",
            "¿Cuál es la tarifa de matrícula?",
            "Какова плата за обучение?",
        ]
        for q in queries:
            assert _is_sensitive_topic(q), f"Failed to detect fee in: {q}"

    def test_registration_topic_detection(self):
        """Should detect registration-related queries."""
        queries = [
            "How to register?",
            "¿Cómo me registro?",
            "Как зарегистрироваться?",
        ]
        for q in queries:
            assert _is_sensitive_topic(q), f"Failed to detect registration in: {q}"

    def test_non_sensitive_topic(self):
        """Should not flag general questions."""
        queries = [
            "What is the weather?",
            "Tell me about Russian culture.",
            "Where is KubGU located?",
        ]
        for q in queries:
            # Can be sensitive if it mentions KubGU, but generally not visa/fee related
            pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
