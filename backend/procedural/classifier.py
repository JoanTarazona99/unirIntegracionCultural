"""Deterministic multilingual classification of student procedures."""

from __future__ import annotations

import unicodedata
from typing import Dict, Iterable, Optional

from app.api.models import ProcedureClassification
from procedural.language import ProcedureLanguageRouter
from retrieval.chunks import tokenize


class ProcedureClassifier:
    """Classify intent without inventing missing profile facts."""

    PROCEDURE_TYPES = (
        "visa",
        "registration",
        "enrollment",
        "housing",
        "migration",
        "other",
    )
    _KEYWORDS = {
        "visa": {
            "visa", "visado", "visum", "виз", "prorroga", "prorrogar",
            "extension", "extend", "продлен", "visto", "vize", "签证", "تأشيرة",
            "thị thực", "thị", "վիզա", "վիզ", "виза", "studentenvisum",
        },
        "registration": {
            "registro", "registrar", "registration", "register", "регистрац",
            "empadronamiento", "mfc", "мфц", "ufms", "уфмс", "enregistrement",
            "anmeldung", "registrierung", "registrazione", "kayıt", "kayit", "登记",
            "تسجيل", "đăng ký", "đăng", "գրանցում", "тіркеу",
        },
        "enrollment": {
            "matricula", "inscripcion", "admision", "enrollment", "enrolment",
            "admission", "apply", "поступ", "зачислен", "прием", "приём",
            "inscription", "einschreibung", "zulassung", "iscrizione", "immatricolazione",
            "入学", "التحاق", "nhập học", "nhập", "ընդունելություն", "қабылдау",
            "kabul",
        },
        "housing": {
            "vivienda", "alojamiento", "dormitorio", "residencia", "housing",
            "accommodation", "dormitory", "hostel", "общежит", "жиль", "logement",
            "wohnheim", "unterkunft", "moradia", "alloggio", "yurt", "konut", "住宿",
            "سكن", "nhà ở", "ký túc xá", "հանրակացարան", "жатақхана",
            "nhà",
        },
        "migration": {
            "migracion", "migratorio", "migration", "migration card",
            "tarjeta de migracion", "миграц", "миграционная карта", "guvm", "гувм",
            "migrazione", "migração", "migration", "göç", "移民", "هجرة", "di trú",
            "trú", "միգրացիա", "көші-қон", "көші",
        },
    }
    _PHRASES = {
        "visa": ("visa de estudiante", "student visa", "студенческ виз", "学生签证"),
        "registration": (
            "registro migratorio", "migration registration", "миграционн регистрац",
            "registro en el lugar", "place of stay registration",
        ),
        "enrollment": (
            "matricula universitaria", "university enrollment", "university admission",
            "прием иностранных", "приём иностранных",
        ),
        "housing": ("residencia universitaria", "student housing", "student dormitory"),
        "migration": ("tarjeta de migracion", "migration card", "миграционная карта"),
    }
    _RETRIEVAL_SOURCE_HINTS = {
        "МВД РФ": ("visa", "registration", "migration"),
        "ГУВМ МВД": ("visa", "migration"),
        "МФЦ": ("registration",),
        "Госуслуги": ("visa", "registration"),
        "КубГУ": ("enrollment", "housing"),
        "Жильё": ("housing",),
    }
    _REQUIRED_PROFILE_FIELDS = {
        "visa": ("country", "visa_type"),
        "registration": ("country", "visa_type"),
        "enrollment": ("academic_level",),
        "housing": ("housing_type",),
        "migration": ("country", "visa_type"),
        "other": (),
    }

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", (value or "").casefold())
        return "".join(char for char in normalized if not unicodedata.combining(char))

    @staticmethod
    def _profile_dict(user_profile) -> Dict:
        if user_profile is None:
            return {}
        if hasattr(user_profile, "model_dump"):
            return user_profile.model_dump(exclude_none=True)
        if isinstance(user_profile, dict):
            nested = user_profile.get("profile")
            return dict(nested if isinstance(nested, dict) else user_profile)
        return {}

    def classify(
        self,
        query: str,
        user_profile=None,
        *,
        retrieved_chunks: Optional[Iterable] = None,
    ) -> ProcedureClassification:
        normalized_query = self._normalize(query)
        detected_language = ProcedureLanguageRouter.detect(query)
        query_tokens = set(tokenize(normalized_query))
        scores = {procedure_type: 0.0 for procedure_type in self.PROCEDURE_TYPES[:-1]}
        matched = {procedure_type: [] for procedure_type in scores}

        for procedure_type, phrases in self._PHRASES.items():
            for phrase in phrases:
                normalized_phrase = self._normalize(phrase)
                if normalized_phrase in normalized_query:
                    scores[procedure_type] += 2.5
                    matched[procedure_type].append(phrase)

        for procedure_type, keywords in self._KEYWORDS.items():
            for keyword in keywords:
                normalized_keyword = self._normalize(keyword)
                if (
                    normalized_keyword in query_tokens
                    or any(token.startswith(normalized_keyword) for token in query_tokens)
                ):
                    scores[procedure_type] += 1.0
                    matched[procedure_type].append(keyword)

        for chunk in retrieved_chunks or ():
            source = getattr(chunk, "source", None)
            if source is None and isinstance(chunk, dict):
                source = chunk.get("source")
            for hinted_type in self._RETRIEVAL_SOURCE_HINTS.get(source, ()):
                scores[hinted_type] += 0.15

        profile = self._profile_dict(user_profile)
        if profile.get("housing_type") and any(
            marker in normalized_query for marker in ("vivir", "live", "жить")
        ):
            scores["housing"] += 0.2
        if profile.get("academic_level") and any(
            marker in normalized_query for marker in ("estudiar", "study", "учиться")
        ):
            scores["enrollment"] += 0.2

        ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        best_type, best_score = ordered[0]
        second_score = ordered[1][1]
        if best_score == 0.0:
            best_type = "other"
            confidence = 0.25
        else:
            confidence = min(0.99, 0.70 + 0.08 * best_score)
            if second_score and best_score - second_score < 0.75:
                confidence = min(confidence, 0.59)

        missing_fields = [
            field
            for field in self._REQUIRED_PROFILE_FIELDS[best_type]
            if not profile.get(field)
        ]
        clarification_questions = []
        if best_type == "other" or confidence < 0.6:
            clarification_questions.append(
                "¿Qué trámite necesitas realizar: visa, registro, matrícula, vivienda o migración?"
            )
        for field in missing_fields:
            questions = {
                "country": "¿Cuál es tu país de ciudadanía?",
                "visa_type": "¿Qué tipo de visa o régimen de entrada tienes?",
                "academic_level": "¿Cuál es tu modalidad o nivel de estudios?",
                "housing_type": "¿Vives en residencia universitaria o en alojamiento privado?",
            }
            clarification_questions.append(questions[field])

        alternatives = {
            procedure_type: round(score, 3)
            for procedure_type, score in ordered[1:]
            if score > 0
        }
        return ProcedureClassification(
            procedure_type=best_type,
            detected_language=detected_language,
            confidence=round(confidence, 3),
            matched_terms=sorted(set(matched.get(best_type, []))),
            alternative_candidates=alternatives,
            missing_profile_fields=missing_fields,
            clarification_questions=clarification_questions,
        )