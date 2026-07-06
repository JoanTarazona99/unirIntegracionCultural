"""
Lightweight, dependency-free faithfulness estimation with multi-level grounding.

Enhanced groundedness evaluation combining:
- Lexical overlap (existing)
- Hard entity matching (numbers, dates, key terms)
- Semantic equivalence heuristics
- Multi-level classification (high/medium/low)

For high-stakes domains an LLM-based faithfulness metric (e.g. RAGAS / NLI) is
ideal, but it requires an LLM and network access. This module provides a
CPU-only, deterministic proxy that estimates how well an answer is grounded
in the retrieved context. It is used as an abstention signal and as a cheap
always-available complement to LLM-as-a-judge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Dict, Tuple, Optional

# Reuse the retrieval tokenizer for consistent multilingual tokenization.
try:
    from retrieval.chunks import tokenize
except Exception:  # pragma: no cover - fallback if import path differs
    _TOKEN_RE = re.compile(r"\w+", re.UNICODE)

    def tokenize(text: str) -> List[str]:
        return _TOKEN_RE.findall((text or "").lower())


class GroundingLevel(Enum):
    """Enum for grounding confidence levels."""
    HIGH = "high"      # >= 0.75: confident, safe to respond
    MEDIUM = "medium"  # 0.4-0.75: partial support, respond with care
    LOW = "low"        # < 0.4: insufficient support, abstain or acquire


@dataclass
class GroundingAnalysis:
    """Detailed grounding analysis result."""
    score: float
    level: GroundingLevel
    explanation: str
    matched_entities: List[str] = None
    missing_entities: List[str] = None
    hard_match_score: float = 0.0
    lexical_score: float = 0.0

    def __post_init__(self):
        if self.matched_entities is None:
            self.matched_entities = []
        if self.missing_entities is None:
            self.missing_entities = []


_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?", re.UNICODE)

# Very common tokens carry little grounding evidence; ignore them so overlap
# reflects content words. Small multilingual stoplist (ES/EN/RU).
_STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "para", "por",
    "que", "con", "del", "se", "su", "es", "the", "a", "an", "of", "to", "in",
    "and", "or", "for", "is", "are", "you", "your", "и", "в", "на", "по", "с",
    "для", "не", "что", "как", "это",
}

# ============ HARD ENTITY EXTRACTION ============

def _extract_numbers(text: str) -> List[str]:
    """Extract all numbers, language levels, and numeric identifiers from text.
    
    Matches: 123, 123.45, 123,45 (European), 50%, ranges (100-200),
    language levels (A1-C2), and other alphanumeric codes.
    """
    # Matches pure numbers
    numbers = re.findall(r'\d+(?:[.,]\d+)?(?:%)?|\d+\s*[-–]\s*\d+(?:[.,]\d+)?', text or "")
    # Also match language levels (A1, A2, B1, B2, C1, C2)
    levels = re.findall(r'\b[A-C][12]\b', text or "", re.IGNORECASE)
    return numbers + levels


def _extract_dates(text: str) -> List[str]:
    """Extract dates in various formats."""
    # Matches: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD, month names, day names
    patterns = [
        r'\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}',  # Various date formats
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)',
        r'(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
        r'(?:январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь)',
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text or "", re.IGNORECASE))
    return results


def _extract_currency_amounts(text: str) -> List[str]:
    """Extract currency amounts and prices."""
    # Matches: $100, 100 USD, 100 rublos, 100 руб, €50, £200, etc.
    pattern = r'(?:[$€£¥₽]?\s*\d+(?:[.,]\d+)?(?:\s*(?:USD|EUR|GBP|JPY|RUB|руб(?:лей)?|дол(?:ларов)?|евро))?|\d+\s*(?:USD|EUR|GBP|JPY|RUB|руб(?:лей)?|дол(?:ларов)?|евро))'
    return re.findall(pattern, text or "", re.IGNORECASE)


def _extract_domain_terms(text: str) -> List[str]:
    """Extract domain-specific terms (visa, registration, course, etc.)."""
    # Domain terms in migration/education context
    domain_keywords = [
        # Visa/migration (English, Spanish, Russian)
        'visa', 'visado', 'visа', 'миграционный', 'регистрация', 'registration',
        'residente', 'residencia', 'резидент', 'temporary_residence', 'виза',
        'mvi', 'мвд',
        # Education/course
        'course', 'curso', 'курс', 'preparatory', 'preparatorio', 'подготовительный',
        'bachelor', 'licenciatura', 'бакалавриат', 'master', 'магистратура',
        'language', 'idioma', 'язык', 'russian', 'ruso', 'русский',
        'trki', 'certificate', 'certificado', 'сертификат',
        # Institutions
        'kubgu', 'кубгу', 'mfc', 'мфц', 'университет', 'university',
    ]
    found = []
    text_lower = (text or "").lower()
    for keyword in domain_keywords:
        if keyword in text_lower:
            found.append(keyword)
    return found


def _extract_time_durations(text: str) -> List[str]:
    """Extract time durations (3 months, 6 weeks, 1 year, etc.)."""
    # Matches: 3 months, 6 semanas, 2 года, etc.
    patterns = [
        r'\d+\s*(?:day|days|dia|días|день|дни|недел(?:я|и|ь)?)',
        r'\d+\s*(?:week|weeks|semana|semanas|неделя|недели)',
        r'\d+\s*(?:month|months|mes|meses|месяц|месяца|месяцев)',
        r'\d+\s*(?:year|years|año|años|год|года|лет)',
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text or "", re.IGNORECASE))
    return results


def _extract_emails_and_contacts(text: str) -> List[str]:
    """Extract email addresses, phone numbers, and URLs."""
    results = []
    # Emails: user@domain.ru, user@domain.com, etc.
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text or "")
    results.extend(emails)
    # Phone numbers: +7-861-XXX-XXXX, +7(861)XXX-XXXX, etc.
    phones = re.findall(r'\+?\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}', text or "")
    results.extend(phones)
    return results


def _hard_match_entities(answer: str, contexts: Iterable[str]) -> Tuple[float, List[str], List[str]]:
    """
    Hard matching of critical entities: numbers, dates, currency, domain terms, emails, contacts.
    Returns: (hard_match_score, matched_entities, missing_entities)
    """
    # Extract entities from answer
    answer_numbers = set(_extract_numbers(answer))
    answer_dates = set(_extract_dates(answer))
    answer_currency = set(_extract_currency_amounts(answer))
    answer_durations = set(_extract_time_durations(answer))
    answer_domain_terms = set(_extract_domain_terms(answer))
    answer_emails = set(_extract_emails_and_contacts(answer))

    # Build context entity set
    context_str = " ".join(contexts)
    context_numbers = set(_extract_numbers(context_str))
    context_dates = set(_extract_dates(context_str))
    context_currency = set(_extract_currency_amounts(context_str))
    context_durations = set(_extract_time_durations(context_str))
    context_domain_terms = set(_extract_domain_terms(context_str))
    context_emails = set(_extract_emails_and_contacts(context_str))

    # Check matches
    matched = []
    missing = []

    # Emails & contacts (CRITICAL for matriculation info - strict match)
    for email in answer_emails:
        if email in context_emails or email.lower() in {e.lower() for e in context_emails}:
            matched.append(f"email:{email}")
        elif answer_emails:
            missing.append(f"email:{email}")

    # Numbers (strict match - especially for language levels like B1/C1)
    # Track conflicts too
    conflicts = []
    for num in answer_numbers:
        if num in context_numbers:
            matched.append(f"number:{num}")
        elif answer_numbers and context_numbers:
            # For language level matching (A1-C2), require EXACT match
            if any(level in num.lower() for level in ['a1', 'a2', 'b1', 'b2', 'c1', 'c2']):
                # Language level: must match exactly
                # Check if a DIFFERENT level exists in context
                conflicting_levels = [ctx for ctx in context_numbers 
                                     if any(l in ctx.lower() for l in ['a1', 'a2', 'b1', 'b2', 'c1', 'c2'])
                                     and ctx.lower() != num.lower()]
                if conflicting_levels:
                    conflicts.append(f"CONFLICT:level {num} vs {conflicting_levels[0]}")
                    missing.append(f"number:{num}")
                else:
                    missing.append(f"number:{num}")
            else:
                # For other numbers, allow 10% tolerance
                try:
                    ans_val = float(num.replace(",", ".").rstrip("%"))
                    for ctx_num in context_numbers:
                        ctx_val = float(ctx_num.replace(",", ".").rstrip("%"))
                        if abs(ans_val - ctx_val) / max(abs(ctx_val), 1) < 0.1:
                            matched.append(f"number_approx:{num}")
                            break
                    else:
                        missing.append(f"number:{num}")
                except Exception:
                    missing.append(f"number:{num}")
        elif answer_numbers:
            missing.append(f"number:{num}")
    
    # Penalize conflicts
    if conflicts:
        missing.extend(conflicts)

    # Dates
    for date in answer_dates:
        if date in context_dates or date.lower() in {d.lower() for d in context_dates}:
            matched.append(f"date:{date}")
        elif answer_dates:
            missing.append(f"date:{date}")

    # Currency
    for curr in answer_currency:
        if curr in context_currency or curr.lower() in {c.lower() for c in context_currency}:
            matched.append(f"currency:{curr}")
        elif answer_currency:
            missing.append(f"currency:{curr}")

    # Durations
    for dur in answer_durations:
        if dur in context_durations or dur.lower() in {d.lower() for d in context_durations}:
            matched.append(f"duration:{dur}")
        elif answer_durations:
            missing.append(f"duration:{dur}")

    # Domain terms
    for term in answer_domain_terms:
        if term in context_domain_terms:
            matched.append(f"term:{term}")

    # Compute hard match score
    all_entities = (answer_numbers | answer_dates | answer_currency | 
                   answer_durations | answer_domain_terms | answer_emails)
    if not all_entities:
        # No critical entities -> neutral score (rely on lexical)
        return 0.5, matched, missing
    
    hard_score = len(matched) / len(all_entities)
    
    # Penalize conflicts: if critical info conflicts, reduce score significantly
    conflict_count = sum(1 for m in missing if 'CONFLICT' in m)
    if conflict_count > 0:
        # Each conflict reduces score by 0.2
        hard_score = max(0.0, hard_score - 0.2 * conflict_count)
    
    return hard_score, matched, missing


def _content_tokens(text: str) -> List[str]:
    return [t for t in tokenize(text) if len(t) > 2 and t not in _STOPWORDS]


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_RE.findall(text or "") if s.strip()]


def sentence_support(sentence: str, context_tokens: set) -> float:
    """Fraction of a sentence's content tokens present in the context."""
    tokens = _content_tokens(sentence)
    if not tokens:
        return 1.0  # Nothing to verify (e.g. greeting) -> treat as supported.
    supported = sum(1 for t in set(tokens) if t in context_tokens)
    return supported / len(set(tokens))


def estimate_faithfulness(answer: str, contexts: Iterable[str]) -> float:
    """
    Estimate how faithful an answer is to the retrieved contexts.

    Returns a score in [0, 1]: the mean per-sentence content-token support of
    the answer against the union of context tokens. Higher = better grounded.
    """
    context_tokens = set()
    for ctx in contexts:
        context_tokens.update(_content_tokens(ctx))
    if not context_tokens:
        return 0.0

    sentences = _split_sentences(answer)
    if not sentences:
        return 0.0

    scores = [sentence_support(s, context_tokens) for s in sentences]
    return sum(scores) / len(scores)


def analyze_grounding_improved(
    answer: str,
    contexts: Iterable[str],
    domain_critical_threshold: float = 0.5,
) -> GroundingAnalysis:
    """
    Improved grounding analysis combining lexical overlap and hard entity matching.

    For high-stakes migration/education domain, this helps distinguish between:
    - Responses with partial but real support (not 0%)
    - Responses lacking critical data (numbers, dates, domain terms)
    - Responses with strong support

    Args:
        answer: Generated response text
        contexts: Retrieved context texts
        domain_critical_threshold: For domain-critical content (visa, fees, durations),
                                  require this fraction of entities to match

    Returns:
        GroundingAnalysis with score, level, explanation, and entity details
    """
    contexts_list = list(contexts)

    # 1. Lexical overlap score (existing method)
    lexical_score = estimate_faithfulness(answer, contexts_list)

    # 2. Hard entity matching
    hard_score, matched_entities, missing_entities = _hard_match_entities(answer, contexts_list)

    # 3. Determine if this is domain-critical content
    critical_terms = ['visa', 'visado', 'виза', 'fee', 'tariff', 'тариф',
                     'course', 'курс', 'duration', 'duration', 'duración',
                     'регистрация', 'registration', 'registro']
    is_domain_critical = any(term.lower() in answer.lower() for term in critical_terms)

    # 4. Combine scores
    # For domain-critical: weight hard matching more heavily (60% hard, 40% lexical)
    # For general: equal weight (50/50)
    if is_domain_critical and (matched_entities or missing_entities):
        combined_score = 0.6 * hard_score + 0.4 * lexical_score
    else:
        combined_score = 0.5 * hard_score + 0.5 * lexical_score

    # 5. Classify level
    if combined_score >= 0.75:
        level = GroundingLevel.HIGH
        explanation = "Response is well-supported by retrieved documents with matching entities."
    elif combined_score >= 0.4:
        level = GroundingLevel.MEDIUM
        explanation = "Response has partial support; some entities match but with gaps."
    else:
        level = GroundingLevel.LOW
        explanation = "Response has insufficient grounding; critical information not found in sources."

    return GroundingAnalysis(
        score=combined_score,
        level=level,
        explanation=explanation,
        matched_entities=matched_entities,
        missing_entities=missing_entities,
        hard_match_score=hard_score,
        lexical_score=lexical_score,
    )

