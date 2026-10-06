"""Generate structured procedures from retrieved, traceable evidence."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

from app.api.models import ProcedureStep, ProceduralRecommendation


class ProcedureGenerator:
    """Deterministic extractor; templates provide structure, never facts."""

    _NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.+?)\s*$")
    _BULLET_RE = re.compile(r"^\s*[-*•]\s+(.+?)\s*$")
    _DAY_RANGE_RE = re.compile(
        r"(\d+)\s*[-–]\s*(\d+)\s*"
        r"(?:business\s+|working\s+|рабоч\w*\s+)?(?:days?|d[ií]as?|дн\w*)",
        re.IGNORECASE,
    )
    _DAY_RE = re.compile(
        r"(?:within\s+|dentro\s+de\s+|за\s+|в\s+течение\s+)?"
        r"(\d+)\s*(?:business\s+|working\s+)?(?:days?|d[ií]as?|дн\w*)",
        re.IGNORECASE,
    )
    _MONTH_RE = re.compile(
        r"(\d+)\s*(?:months?|mes(?:es)?|месяц\w*)",
        re.IGNORECASE,
    )
    _HEADINGS = {
        "process": (
            "proceso", "procedimiento", "process", "procedure", "процесс",
            "процедура", "как", "продление визы", "visa extension",
            "extension de visa", "extensión de visado",
        ),
        "documents": ("documentos", "documents", "документы", "требования", "requirements"),
        "deadline": (
            "plazo", "plazos", "deadline", "processing time", "срок", "сроки",
            "calendario financiero",
            "tiempo de procesamiento", "время обработки",
        ),
        "entity": ("organismo", "responsable", "responsible", "place", "lugar", "место", "где"),
    }
    _ENTITY_BY_SOURCE = {
        "МВД РФ": "Ministerio del Interior de la Federación Rusa (МВД РФ)",
        "ГУВМ МВД": "Dirección General de Migración del МВД (ГУВМ МВД)",
        "МФЦ": "Centro Multifuncional (МФЦ)",
        "Госуслуги": "Portal Госуслуги / organismo seleccionado",
        "КубГУ": "Universidad Estatal de Kubán (КубГУ)",
        "FAQ": "Universidad Estatal de Kubán (КубГУ)",
        "Документы": "Universidad y autoridad documental competente",
    }

    @staticmethod
    def _as_dict(chunk) -> Dict:
        if isinstance(chunk, dict):
            return dict(chunk)
        metadata = dict(getattr(chunk, "metadata", {}) or {})
        return {
            "id": getattr(chunk, "id", ""),
            "source": getattr(chunk, "source", ""),
            "title": getattr(chunk, "title", ""),
            "content": getattr(chunk, "content", ""),
            "source_url": getattr(chunk, "source_url", None),
            "evidence_confidence": metadata.get("evidence_confidence", 0.6),
            "metadata": metadata,
        }

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

    @classmethod
    def _heading_type(cls, line: str) -> Optional[str]:
        normalized = line.casefold().strip().rstrip(":")
        for heading_type, markers in cls._HEADINGS.items():
            if any(normalized.startswith(marker) for marker in markers):
                return heading_type
        return None

    @classmethod
    def _deadline_days(cls, deadline_text: Optional[str]) -> Optional[int]:
        if not deadline_text:
            return None
        match = cls._DAY_RANGE_RE.search(deadline_text)
        if match:
            return int(match.group(2))
        match = cls._DAY_RE.search(deadline_text)
        if match:
            return int(match.group(1))
        match = cls._MONTH_RE.search(deadline_text)
        if match:
            return int(match.group(1)) * 30
        return None

    @classmethod
    def _extract_chunk(cls, chunk: Dict) -> Tuple[List[str], List[str], Optional[str], Optional[str]]:
        actions: List[str] = []
        documents: List[str] = []
        deadline_text = None
        responsible_entity = None
        section = None

        for raw_line in str(chunk.get("content") or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            inline_heading = cls._heading_type(line)
            if inline_heading:
                section = inline_heading
                if ":" in line:
                    value = line.split(":", 1)[1].strip()
                    if inline_heading == "deadline" and value and deadline_text is None:
                        deadline_text = value
                    elif inline_heading == "entity" and value:
                        responsible_entity = value
                continue
            if ":" in line:
                heading_candidate = line.split(":", 1)[0]
                letters = [char for char in heading_candidate if char.isalpha()]
                uppercase_ratio = (
                    sum(char.isupper() for char in letters) / len(letters)
                    if letters else 0.0
                )
                if uppercase_ratio >= 0.7:
                    section = None
                    continue

            numbered = cls._NUMBERED_RE.match(line)
            bullet = cls._BULLET_RE.match(line)
            item = numbered.group(2) if numbered else bullet.group(1) if bullet else None
            if item is not None:
                item_heading = cls._heading_type(item)
                if item_heading and ":" in item:
                    value = item.split(":", 1)[1].strip()
                    if item_heading == "deadline" and value and deadline_text is None:
                        deadline_text = value
                    elif item_heading == "entity" and value:
                        responsible_entity = value
                    continue
                if section == "documents":
                    documents.append(item)
                elif section == "deadline" and deadline_text is None:
                    deadline_text = item
                elif section == "process" or numbered:
                    actions.append(item)
                    deadline_markers = (
                        "before", "within", "dentro", "antes", "days", "dias", "días",
                        "months", "mes", "дней", "дня", "месяц", "до истеч",
                    )
                    if deadline_text is None and any(
                        marker in item.casefold() for marker in deadline_markers
                    ):
                        deadline_text = item
                continue

            if section == "deadline" and deadline_text is None:
                deadline_text = line
            elif section == "entity" and responsible_entity is None:
                responsible_entity = line

        return actions, documents, deadline_text, responsible_entity

    @staticmethod
    def _confidence(chunk: Dict) -> float:
        raw = chunk.get(
            "evidence_confidence",
            chunk.get("relevance", chunk.get("score", 0.6)),
        )
        try:
            score = float(raw)
        except (TypeError, ValueError):
            score = 0.5
        return max(0.0, min(1.0, score))

    def generate_steps(
        self,
        procedure_type: str,
        retrieved_chunks: Iterable,
        user_profile=None,
        *,
        retrieval_mode: str = "unknown",
        correlation_id: str = "",
    ) -> ProceduralRecommendation:
        chunks = [self._as_dict(chunk) for chunk in retrieved_chunks]
        steps: List[ProcedureStep] = []
        warnings: List[str] = []

        for chunk in chunks:
            source_url = chunk.get("source_url") or chunk.get("url")
            source_title = str(chunk.get("title") or "").strip()
            chunk_id = str(chunk.get("id") or chunk.get("chunk_id") or "").strip()
            if not source_url or not source_title or not chunk_id:
                warnings.append("Se descartó evidencia sin URL, título o chunk_id trazable.")
                continue

            actions, documents, deadline_text, explicit_entity = self._extract_chunk(chunk)
            entity = explicit_entity or self._ENTITY_BY_SOURCE.get(chunk.get("source"))
            if not actions:
                actions = [source_title]

            metadata = dict(chunk.get("metadata") or {})
            version_id = metadata.get("version_id") or chunk.get("version_id")
            confidence = self._confidence(chunk)
            for action_index, action in enumerate(actions):
                step_documents = documents if action_index == 0 else []
                steps.append(
                    ProcedureStep(
                        step_number=len(steps) + 1,
                        title=action[:160],
                        description=action,
                        required_documents=step_documents,
                        deadline_days=self._deadline_days(deadline_text),
                        deadline_text=deadline_text,
                        responsible_entity=entity,
                        source_url=source_url,
                        source_title=source_title,
                        evidence_confidence=confidence,
                        evidence_chunk_ids=[chunk_id],
                        source_version_id=version_id,
                    )
                )

        evidence_sufficient = bool(steps) and all(
            step.evidence_confidence >= 0.5 and step.evidence_chunk_ids
            for step in steps
        )
        return ProceduralRecommendation(
            status="complete" if evidence_sufficient else "abstained",
            procedure_type=procedure_type,
            classification_confidence=1.0,
            user_profile_context=self._profile_dict(user_profile),
            steps=steps if evidence_sufficient else [],
            total_estimated_days=None,
            warnings=warnings,
            missing_information=[] if evidence_sufficient else ["verified_procedure_steps"],
            clarification_questions=[],
            evidence_sufficient=evidence_sufficient,
            abstention_reason=None if evidence_sufficient else "insufficient_step_evidence",
            retrieval_mode=retrieval_mode,
            correlation_id=correlation_id,
        )