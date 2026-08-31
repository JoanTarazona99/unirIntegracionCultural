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
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Tuple

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


@dataclass
class EvidenceAssessment:
    """Query-to-evidence sufficiency evaluated independently of the answer."""

    query_relevance: float
    query_term_coverage: float
    query_entity_coverage: float
    requested_slot_coverage: bool
    retrieval_confidence: float
    sufficient: bool
    reasons: List[str]
    query_terms: List[str]
    matched_terms: List[str]
    missing_terms: List[str]
    query_entities: Dict[str, List[str]]
    matched_entities: Dict[str, List[str]]
    missing_entities: Dict[str, List[str]]
    requested_slot: Optional[str] = None

    @property
    def score(self) -> float:
        """Conservative aggregate for reporting, not the sufficiency decision."""
        slot_score = 1.0 if self.requested_slot_coverage else 0.0
        return (
            0.35 * self.query_relevance
            + 0.20 * self.query_term_coverage
            + 0.20 * self.query_entity_coverage
            + 0.15 * slot_score
            + 0.10 * self.retrieval_confidence
        )


_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?", re.UNICODE)

# Very common tokens carry little grounding evidence; ignore them so overlap
# reflects content words. Small multilingual stoplist (ES/EN/RU).
_STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "para", "por",
    "que", "con", "del", "se", "su", "es", "the", "a", "an", "of", "to", "in",
    "and", "or", "for", "is", "are", "you", "your", "и", "в", "на", "по", "с",
    "для", "не", "что", "как", "это",
}

_QUERY_STOPWORDS = _STOPWORDS | {
    "cual", "cuál", "cuando", "cuándo", "donde", "dónde", "como", "cómo",
    "what", "when", "where", "which", "who", "please", "porfavor",
    "какой", "какая", "какие", "когда", "где", "кто", "ли",
}

_MONTH_NAMES = (
    "january|february|march|april|may|june|july|august|september|october|"
    "november|december|enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    "septiembre|octubre|noviembre|diciembre|января|февраля|марта|апреля|мая|"
    "июня|июля|августа|сентября|октября|ноября|декабря"
)

_REQUESTED_SLOT_PATTERNS = {
    "purpose_of_stay": (
        (),
        re.compile(
            r"(?:\b(?:purpose of (?:stay|visit)|reason for (?:travel|entry))\b"
            r"[\s\S]{0,100}?\b(?:study|education|tourism|work|private visit)\b|"
            r"\b(?:study|education|tourism|work|private visit)\b[\s\S]{0,100}?"
            r"\b(?:purpose of (?:stay|visit)|reason for (?:travel|entry))\b)",
            re.IGNORECASE,
        ),
    ),
    "documents": (
        (),
        re.compile(
            r"\b(?:documents?|passport|migration card|visa|application form|"
            r"documentos?|pasaporte|tarjeta migratoria|visado|visa|"
            r"документ\w*|паспорт\w*|миграционн\w+ карт\w*|виз\w*)\b",
            re.IGNORECASE,
        ),
    ),
    "required_action": (
        (),
        re.compile(
            r"\b(?:must|should|required to|need to|has to|notify|inform|report|"
            r"submit|register|update|contact|apply|debe\w*|tiene que|notific\w*|"
            r"inform\w*|present\w*|registr\w*|actualiz\w*|"
            r"долж\w*|нужн\w*|уведом\w*|сообщ\w*|подат\w*|зарегистр\w*)\b",
            re.IGNORECASE,
        ),
    ),
    "code": (
        ("codigo", "code", "код"),
        re.compile(
            r"\b(?:c[oó]digo|code|код)\b[\s\S]{0,80}?"
            r"\b(?=[A-ZА-Я0-9-]*[A-ZА-Я])(?=[A-ZА-Я0-9-]*\d)"
            r"[A-ZА-Я0-9]+(?:-[A-ZА-Я0-9]+)+\b",
            re.IGNORECASE,
        ),
    ),
    "date": (
        ("fecha", "date", "deadline", "cuando", "когда", "дата"),
        re.compile(
            rf"\b(?:\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}|"
            rf"\d{{1,2}}\s+(?:de\s+)?(?:{_MONTH_NAMES})(?:\s+(?:de\s+)?\d{{4}})?|"
            rf"(?:within|in)\s+\d+\s+(?:days?|weeks?|months?|years?)|"
            rf"(?:before|after|by)\s+(?:\d{{1,2}}|(?:{_MONTH_NAMES})))\b",
            re.IGNORECASE,
        ),
    ),
    "requirement": (
        ("requisit", "necesit", "requier", "require", "must", "требован", "нужн"),
        re.compile(r"\b(?:requisit\w*|necesit\w*|requier\w*|requir\w*|must|требован\w*|нужн\w*)\b", re.IGNORECASE),
    ),
    "cost": (
        ("precio", "costo", "coste", "tarifa", "price", "cost", "fee", "стоимост", "цена", "тариф"),
        re.compile(r"(?:[$€£¥₽]\s*\d|\d[\d.,]*\s*(?:USD|EUR|RUB|руб|rubles?|rublos?))", re.IGNORECASE),
    ),
    "contact": (
        ("contact", "correo", "email", "telefono", "phone", "контакт", "почт", "телефон"),
        re.compile(r"(?:\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b|\+\d[\d() .-]{6,})"),
    ),
    "location": (
        ("ubicacion", "direccion", "location", "address", "where", "donde", "адрес", "где"),
        re.compile(r"\b(?:ubicad\w*|direcci[oó]n|location|address|наход\w*|адрес)\b", re.IGNORECASE),
    ),
    "duration": (
        ("duracion", "dura", "duration", "long", "срок", "длит"),
        re.compile(r"\b\d+\s*(?:days?|weeks?|months?|years?|d[ií]as?|semanas?|mes(?:es)?|a[nñ]os?|дн\w*|недел\w*|месяц\w*|лет|год\w*)\b", re.IGNORECASE),
    ),
}

_EXPLICIT_SLOT_QUERY_PATTERNS = (
    (
        "purpose_of_stay",
        re.compile(
            r"\b(?:purpose of (?:stay|visit)|reason for (?:travel|entry)|"
            r"proposito (?:de (?:estancia|visita)|del viaje|de entrada)|"
            r"motivo (?:del viaje|de entrada)|"
            r"цель (?:пребывания|визита|поездки|въезда))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "documents",
        re.compile(
            r"\b(?:what|which)\s+documents?\b|"
            r"\b(?:que|cuales)\s+documentos?\b|"
            r"\b(?:какие|какой)\s+документ\w*\b",
            re.IGNORECASE,
        ),
    ),
    (
        "required_action",
        re.compile(
            r"\bwhat\s+(?:should|must|does|do|can)\b[\s\S]{0,100}?\bdo\b|"
            r"\bque\s+(?:debe|deberia|tiene que)\b[\s\S]{0,100}?\b(?:hacer|realizar)\b|"
            r"\bчто\s+(?:долж\w*|нужн\w*)\b[\s\S]{0,100}?\b(?:делать|сделать)\b",
            re.IGNORECASE,
        ),
    ),
)

_DATE_QUESTION_PATTERN = re.compile(
    r"^(?:when|cuando|когда)\b|\b(?:what|which)\s+date\b|"
    r"\b(?:que|cual)\s+fecha\b|\b(?:какая|какой)\s+дата\b|\bdeadline\b",
    re.IGNORECASE,
)


def _normalize_for_matching(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _detect_requested_slot(query: str) -> Optional[str]:
    normalized_query = _normalize_for_matching(query).strip()
    for slot_name, query_pattern in _EXPLICIT_SLOT_QUERY_PATTERNS:
        if query_pattern.search(normalized_query):
            return slot_name

    if _DATE_QUESTION_PATTERN.search(normalized_query):
        return "date"

    for slot_name, (query_markers, _) in _REQUESTED_SLOT_PATTERNS.items():
        if slot_name in {"purpose_of_stay", "documents", "required_action", "date"}:
            continue
        if any(marker in normalized_query for marker in query_markers):
            return slot_name
    return None


def _informative_query_terms(query: str) -> List[str]:
    terms = []
    for token in tokenize(query):
        normalized = _normalize_for_matching(token)
        if len(normalized) > 2 and normalized not in {_normalize_for_matching(t) for t in _QUERY_STOPWORDS}:
            terms.append(normalized)
    return sorted(set(terms))


def _terms_match(query_term: str, document_term: str) -> bool:
    if query_term == document_term:
        return True
    return min(len(query_term), len(document_term)) >= 5 and (
        query_term.startswith(document_term) or document_term.startswith(query_term)
    )


def _extract_query_entities(query: str) -> Dict[str, List[str]]:
    date_pattern = re.compile(
        rf"\b(?:\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}|"
        rf"\d{{1,2}}\s+(?:de\s+)?(?:{_MONTH_NAMES})\s+(?:de\s+)?\d{{4}})\b",
        re.IGNORECASE,
    )
    code_pattern = re.compile(
        r"\b(?=[A-ZА-Я0-9-]*[A-ZА-Я])(?=[A-ZА-Я0-9-]*\d)"
        r"[A-ZА-Я0-9]+(?:-[A-ZА-Я0-9]+)+\b"
    )
    known_institution_pattern = re.compile(
        r"\b(?:kubgu|kubsu|кубгу|мвд|мфц|госуслуги)\b",
        re.IGNORECASE,
    )
    acronym_pattern = re.compile(r"\b[A-ZА-ЯЁ]{2,}(?![A-ZА-ЯЁ0-9-]*\d)\b")
    codes = code_pattern.findall(query or "")
    institutions = [
        value
        for value in known_institution_pattern.findall(query or "") + acronym_pattern.findall(query or "")
        if value not in codes
    ]
    return {
        "dates": sorted(set(date_pattern.findall(query or ""))),
        "institutions": sorted(set(institutions)),
        "codes": sorted(set(codes)),
    }


def _retrieval_confidence(results: List[Dict[str, Any]], retrieval_mode: str) -> float:
    mode = (retrieval_mode or "").strip().lower()
    if mode == "fallback":
        return 0.0

    scores = []
    for result in results:
        raw_score = result.get("relevance", result.get("score"))
        if raw_score is None:
            continue
        try:
            score = max(0.0, float(raw_score))
        except (TypeError, ValueError):
            continue
        scores.append(min(score, 1.0) if score <= 1.0 else score / (score + 1.0))

    score_confidence = sum(scores) / len(scores) if scores else 0.5
    mode_weight = 0.8 if mode == "keyword" else 1.0
    return max(0.0, min(1.0, score_confidence * mode_weight))


def assess_evidence_sufficiency(
    query: str,
    results: List[Dict[str, Any]],
    *,
    retrieval_top_k: int = 5,
    retrieval_mode: str = "semantic",
    query_relevance_threshold: float = 0.5,
    query_entity_coverage_threshold: float = 1.0,
) -> EvidenceAssessment:
    """Assess query-to-document evidence before answer generation."""
    selected_results = list(results or [])[:max(0, retrieval_top_k)]
    document_texts = [
        " ".join(
            str(result.get(field, "") or "")
            for field in ("title", "content", "source")
        )
        for result in selected_results
    ]
    document_token_sets = [
        {_normalize_for_matching(token) for token in tokenize(text)}
        for text in document_texts
    ]
    all_document_tokens = set().union(*document_token_sets) if document_token_sets else set()
    query_terms = _informative_query_terms(query)

    def matched_terms(tokens: set) -> List[str]:
        return [
            term for term in query_terms
            if any(_terms_match(term, document_term) for document_term in tokens)
        ]

    per_document_coverage = [
        len(matched_terms(tokens)) / len(query_terms) if query_terms else 0.0
        for tokens in document_token_sets
    ]
    matched_query_terms = matched_terms(all_document_tokens)
    query_relevance = max(per_document_coverage, default=0.0)
    query_term_coverage = (
        len(matched_query_terms) / len(query_terms) if query_terms else 0.0
    )

    query_entities = _extract_query_entities(query)
    normalized_evidence = _normalize_for_matching(" ".join(document_texts))
    matched_query_entities: Dict[str, List[str]] = {}
    missing_query_entities: Dict[str, List[str]] = {}
    for entity_type, values in query_entities.items():
        matched_query_entities[entity_type] = [
            value for value in values
            if _normalize_for_matching(value) in normalized_evidence
        ]
        missing_query_entities[entity_type] = [
            value for value in values
            if value not in matched_query_entities[entity_type]
        ]

    entity_count = sum(len(values) for values in query_entities.values())
    matched_entity_count = sum(len(values) for values in matched_query_entities.values())
    query_entity_coverage = matched_entity_count / entity_count if entity_count else 1.0

    requested_slot = _detect_requested_slot(query)
    evidence_text = _normalize_for_matching(" ".join(document_texts))
    requested_slot_coverage = (
        requested_slot is None
        or bool(_REQUESTED_SLOT_PATTERNS[requested_slot][1].search(evidence_text))
    )

    reasons = []
    if not selected_results:
        reasons.append("no_results")
    if (retrieval_mode or "").strip().lower() == "fallback":
        reasons.append("fallback_retrieval")
    if query_relevance < query_relevance_threshold:
        reasons.append("query_relevance_below_threshold")
    if query_entity_coverage < query_entity_coverage_threshold:
        reasons.append("query_entity_coverage_below_threshold")
    if not requested_slot_coverage:
        reasons.append("requested_slot_not_covered")

    sufficient = bool(selected_results) and not reasons
    return EvidenceAssessment(
        query_relevance=query_relevance,
        query_term_coverage=query_term_coverage,
        query_entity_coverage=query_entity_coverage,
        requested_slot_coverage=requested_slot_coverage,
        retrieval_confidence=_retrieval_confidence(selected_results, retrieval_mode),
        sufficient=sufficient,
        reasons=reasons,
        query_terms=query_terms,
        matched_terms=matched_query_terms,
        missing_terms=[term for term in query_terms if term not in matched_query_terms],
        query_entities=query_entities,
        matched_entities=matched_query_entities,
        missing_entities=missing_query_entities,
        requested_slot=requested_slot,
    )

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
    
    hard_score = min(1.0, len(matched) / len(all_entities))
    
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
    combined_score = max(0.0, min(1.0, combined_score))

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

