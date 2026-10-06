"""Offline language detection and conservative evidence-language routing."""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Set, Tuple

from app.api.models import EVIDENCE_LANGUAGES, SUPPORTED_LANGUAGES


class ProcedureLanguageRouter:
    """Route supported query languages to ES/EN/RU evidence conservatively."""

    EVIDENCE_LANGUAGE_BY_QUERY = {
        "es": "es",
        "en": "en",
        "ru": "ru",
        "fr": "es",
        "de": "en",
        "zh": "en",
        "ar": "en",
        "vi": "en",
        "hy": "ru",
        "kk": "ru",
        "pt": "es",
        "it": "es",
        "tr": "en",
    }
    _LATIN_MARKERS = {
        "es": {
            "como", "que", "necesito", "solicitar", "solicitud", "matricula",
            "vivienda", "registro", "pasaporte", "tarjeta", "dentro", "dias", "visa",
        },
        "en": {"how", "what", "need", "apply", "student", "housing"},
        "fr": {"comment", "demander", "etudiant", "étudiant", "logement", "inscription"},
        "de": {"wie", "beantrage", "studentenvisum", "anmeldung", "wohnheim", "einschreibung"},
        "vi": {"lam", "làm", "the", "thẻ", "thi", "thị", "đăng", "ky", "ký", "nhap", "nhập"},
        "pt": {
            "faco", "faço", "preciso", "solicitar", "moradia", "matricula",
            "um", "estudante", "visto",
        },
        "it": {"come", "richiedere", "visto", "alloggio", "iscrizione", "immatricolazione"},
        "tr": {"nasil", "nasıl", "basvur", "başvur", "vize", "kayit", "kayıt", "yurt"},
    }
    _CRITICAL_RE = re.compile(
        r"https?://\S+|[\w.+-]+@[\w.-]+\.\w+|\b\d+(?:[.,-]\d+)*\b|"
        r"\b(?:МВД|МФЦ|ГУВМ|КубГУ|СНИЛС|ИНН|TRKI|RUB|USD|EUR)\b",
        re.IGNORECASE | re.UNICODE,
    )

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", (value or "").casefold())
        return "".join(char for char in normalized if not unicodedata.combining(char))

    @classmethod
    def detect(cls, text: str) -> str:
        value = text or ""
        lowered = value.casefold()
        if re.search(r"\b(?:faço|você|inscrição|solicitação)\b|[ãõ]", lowered):
            return "pt"
        if re.search(r"[\u4e00-\u9fff]", value):
            return "zh"
        if re.search(r"[\u0600-\u06ff]", value):
            return "ar"
        if re.search(r"[\u0530-\u058f]", value):
            return "hy"
        if re.search(r"[әғқңөұүһі]", value.casefold()):
            return "kk"
        if re.search(r"[\u0400-\u04ff]", value):
            return "ru"

        normalized = cls._normalize(value)
        tokens = set(re.findall(r"\w+", normalized, re.UNICODE))
        scores = {
            language: len(tokens & {cls._normalize(marker) for marker in markers})
            for language, markers in cls._LATIN_MARKERS.items()
        }
        best_language, best_score = max(scores.items(), key=lambda item: (item[1], item[0]))
        if best_score:
            return best_language
        return "en"

    @classmethod
    def evidence_language(cls, language: str) -> str:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        target = cls.EVIDENCE_LANGUAGE_BY_QUERY[language]
        if target not in EVIDENCE_LANGUAGES:
            raise ValueError(f"Invalid evidence language: {target}")
        return target

    @classmethod
    def critical_tokens(cls, text: str) -> Set[str]:
        return {token.casefold().rstrip(".,;:)") for token in cls._CRITICAL_RE.findall(text or "")}

    @classmethod
    def preserves_critical_information(cls, source: str, translated: str) -> bool:
        translated_normalized = translated.casefold()
        return all(token in translated_normalized for token in cls.critical_tokens(source))

    @classmethod
    def translate_checked(
        cls,
        text: str,
        *,
        source_language: str,
        target_language: str,
        translator,
    ) -> Tuple[Optional[str], bool]:
        if source_language == target_language:
            return text, False
        if translator is None:
            return None, False
        translated = translator.translate_text(
            text,
            target_language=target_language,
            source_language=source_language,
        )
        if not translated or not translated.strip():
            return None, False
        if cls._normalize(translated) == cls._normalize(text) and len(text.split()) > 2:
            return None, False
        if not cls.preserves_critical_information(text, translated):
            return None, False
        return translated.strip(), True