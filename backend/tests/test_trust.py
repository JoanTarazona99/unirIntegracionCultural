"""Tests for the trustworthy-AI layer (faithfulness + citation/abstention guard)."""

from trust import enforce_grounding, estimate_faithfulness


_RESULTS = [
    {
        "source": "МВД РФ",
        "title": "Регистрация по месту пребывания",
        "content": "Регистрация для иностранцев: в течение 7 дней после прибытия. Документы: паспорт, виза, миграционная карта.",
        "source_url": "https://мвд.рф",
    }
]


def test_faithfulness_high_for_grounded_answer():
    # An answer expressed in the source language grounds strongly.
    answer = "Регистрация в течение 7 дней. Нужны паспорт, виза и миграционная карта."
    score = estimate_faithfulness(answer, [r["content"] for r in _RESULTS])
    assert score > 0.5


def test_faithfulness_low_for_ungrounded_answer():
    answer = "El precio del billete de avión a Moscú es muy barato en diciembre."
    score = estimate_faithfulness(answer, [r["content"] for r in _RESULTS])
    assert score < 0.3


def test_guard_passes_grounded_answer():
    answer = "Регистрация в течение 7 дней. Документы: паспорт, виза, миграционная карта."
    result = enforce_grounding(answer, _RESULTS, threshold=0.35, language="es")
    assert result.grounded is True
    assert result.abstained is False
    assert result.citations
    assert result.answer == answer


def test_guard_abstains_on_hallucination():
    answer = "Los billetes de tren a San Petersburgo cuestan 100 euros en verano."
    result = enforce_grounding(answer, _RESULTS, threshold=0.5, language="es")
    assert result.abstained is True
    assert result.grounded is False
    assert "oficial" in result.answer.lower()


def test_guard_abstains_without_sources():
    result = enforce_grounding("Cualquier respuesta", [], threshold=0.35, language="en")
    assert result.abstained is True
