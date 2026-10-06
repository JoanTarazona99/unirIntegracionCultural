"""Application service for personalized, evidence-checked procedures."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from app.api.models import ProceduralRecommendation, ProceduralRequest
from app.config.logging_config import get_logger
from procedural import ProcedureClassifier, ProcedureEvaluator, ProcedureGenerator
from procedural.language import ProcedureLanguageRouter

logger = get_logger(__name__)


class ProceduralService:
    """Orchestrate profile resolution, retrieval, generation, and fail-closed checks."""

    def __init__(self, rag_service, profile_service, translator=None):
        self.rag_service = rag_service
        self.profile_service = profile_service
        self.translator = translator
        self.classifier = ProcedureClassifier()
        self.generator = ProcedureGenerator()
        self.evaluator = ProcedureEvaluator()
        self.language_router = ProcedureLanguageRouter()

    @staticmethod
    def _stored_profile(payload: Dict) -> Dict:
        if not payload or not payload.get("exists"):
            return {}
        profile = payload.get("profile") or {}
        if isinstance(profile.get("profile"), dict):
            return dict(profile["profile"])
        return dict(profile) if isinstance(profile, dict) else {}

    def _resolve_profile(self, request: ProceduralRequest) -> Dict:
        profile: Dict = {}
        if request.user_id:
            profile = self._stored_profile(
                self.profile_service.get_profile(request.user_id)
            )
        if request.profile is not None:
            profile.update(request.profile.model_dump(exclude_none=True))
        profile.update({key: value for key, value in request.context.items() if value})
        return profile

    @staticmethod
    def _clarification_response(
        classification,
        profile: Dict,
        retrieval_mode: str,
        correlation_id: str,
        *,
        response_language: str,
        evidence_language: str,
        clarification_questions: Optional[Iterable[str]] = None,
    ) -> ProceduralRecommendation:
        return ProceduralRecommendation(
            status="needs_clarification",
            procedure_type=classification.procedure_type,
            language=response_language,
            detected_language=classification.detected_language,
            evidence_language=evidence_language,
            classification_confidence=classification.confidence,
            user_profile_context=profile,
            steps=[],
            warnings=[],
            missing_information=list(classification.missing_profile_fields),
            clarification_questions=list(
                clarification_questions or classification.clarification_questions
            ),
            evidence_sufficient=False,
            abstention_reason=None,
            retrieval_mode=retrieval_mode,
            correlation_id=correlation_id,
        )

    @staticmethod
    def _abstention_response(
        classification,
        profile: Dict,
        retrieval_mode: str,
        correlation_id: str,
        *,
        response_language: str,
        evidence_language: str,
        reasons: Iterable[str],
        translation_applied: bool = False,
    ) -> ProceduralRecommendation:
        reason_list = list(reasons)
        return ProceduralRecommendation(
            status="abstained",
            procedure_type=classification.procedure_type,
            language=response_language,
            detected_language=classification.detected_language,
            evidence_language=evidence_language,
            translation_applied=translation_applied,
            classification_confidence=classification.confidence,
            user_profile_context=profile,
            steps=[],
            warnings=[],
            missing_information=reason_list,
            clarification_questions=[],
            evidence_sufficient=False,
            abstention_reason=";".join(reason_list),
            retrieval_mode=retrieval_mode,
            correlation_id=correlation_id,
        )

    def _translate_strings(
        self,
        values: Iterable[str],
        *,
        source_language: str,
        target_language: str,
    ) -> Optional[list[str]]:
        translated_values = []
        for value in values:
            translated, _ = self.language_router.translate_checked(
                value,
                source_language=source_language,
                target_language=target_language,
                translator=self.translator,
            )
            if translated is None:
                return None
            translated_values.append(translated)
        return translated_values

    def _localize_recommendation(
        self,
        recommendation: ProceduralRecommendation,
        target_language: str,
    ) -> bool:
        translation_applied = False
        for step in recommendation.steps:
            fields = [step.title, step.description]
            if step.deadline_text:
                fields.append(step.deadline_text)
            translated_fields = []
            for field in fields:
                source_language = self.language_router.detect(field)
                translated, applied = self.language_router.translate_checked(
                    field,
                    source_language=source_language,
                    target_language=target_language,
                    translator=self.translator,
                )
                if translated is None:
                    return False
                translated_fields.append(translated)
                translation_applied = translation_applied or applied
            step.title = translated_fields[0]
            step.description = translated_fields[1]
            if step.deadline_text:
                step.deadline_text = translated_fields[2]

            translated_documents = []
            for document in step.required_documents:
                source_language = self.language_router.detect(document)
                translated, applied = self.language_router.translate_checked(
                    document,
                    source_language=source_language,
                    target_language=target_language,
                    translator=self.translator,
                )
                if translated is None:
                    return False
                translated_documents.append(translated)
                translation_applied = translation_applied or applied
            step.required_documents = translated_documents
        recommendation.translation_applied = translation_applied
        return True

    def recommend(
        self,
        request: ProceduralRequest,
        *,
        correlation_id: str,
    ) -> ProceduralRecommendation:
        profile = self._resolve_profile(request)
        initial_classification = self.classifier.classify(request.query, profile)
        detected_language = initial_classification.detected_language
        response_language = request.language or detected_language
        evidence_language = self.language_router.evidence_language(detected_language)

        if initial_classification.confidence < 0.6 or initial_classification.missing_profile_fields:
            questions = initial_classification.clarification_questions
            if response_language != "es":
                questions = self._translate_strings(
                    questions,
                    source_language="es",
                    target_language=response_language,
                )
                if questions is None:
                    return self._abstention_response(
                        initial_classification,
                        profile,
                        "not_run",
                        correlation_id,
                        response_language=response_language,
                        evidence_language=evidence_language,
                        reasons=["clarification_translation_unavailable_or_unsafe"],
                    )
            return self._clarification_response(
                initial_classification,
                profile,
                "not_run",
                correlation_id,
                response_language=response_language,
                evidence_language=evidence_language,
                clarification_questions=questions,
            )

        retrieval_query = request.query
        query_translation_applied = False
        if detected_language != evidence_language:
            retrieval_query, query_translation_applied = self.language_router.translate_checked(
                request.query,
                source_language=detected_language,
                target_language=evidence_language,
                translator=self.translator,
            )
            if retrieval_query is None:
                return self._abstention_response(
                    initial_classification,
                    profile,
                    "not_run",
                    correlation_id,
                    response_language=response_language,
                    evidence_language=evidence_language,
                    reasons=["query_translation_unavailable_or_unsafe"],
                )
            translated_classification = self.classifier.classify(retrieval_query, profile)
            if translated_classification.procedure_type != initial_classification.procedure_type:
                return self._abstention_response(
                    initial_classification,
                    profile,
                    "not_run",
                    correlation_id,
                    response_language=response_language,
                    evidence_language=evidence_language,
                    reasons=["query_translation_changed_procedure_intent"],
                    translation_applied=True,
                )

        evidence = self.rag_service.retrieve_evidence(
            retrieval_query,
            correlation_id=correlation_id,
        )
        results = list(evidence.get("results") or [])
        retrieval_mode = evidence.get("search_mode") or "unknown"
        classification = self.classifier.classify(
            retrieval_query,
            profile,
            retrieved_chunks=results,
        )
        classification.detected_language = detected_language

        if classification.confidence < 0.6 or classification.missing_profile_fields:
            return self._clarification_response(
                classification,
                profile,
                retrieval_mode,
                correlation_id,
                response_language=response_language,
                evidence_language=evidence_language,
            )

        assessment = dict(evidence.get("evidence_assessment") or {})
        if not assessment.get("sufficient", False):
            reasons = list(assessment.get("reasons") or ["insufficient_evidence"])
            return self._abstention_response(
                classification,
                profile,
                retrieval_mode,
                correlation_id,
                response_language=response_language,
                evidence_language=evidence_language,
                reasons=reasons,
                translation_applied=query_translation_applied,
            )

        recommendation = self.generator.generate_steps(
            classification.procedure_type,
            results,
            profile,
            retrieval_mode=retrieval_mode,
            correlation_id=correlation_id,
        )
        recommendation.classification_confidence = classification.confidence
        recommendation.language = response_language
        recommendation.detected_language = detected_language
        recommendation.evidence_language = evidence_language
        recommendation.translation_applied = query_translation_applied
        evaluation = self.evaluator.evaluate(recommendation)
        if not evaluation.sufficient:
            recommendation.status = "abstained"
            recommendation.steps = []
            recommendation.total_estimated_days = None
            recommendation.evidence_sufficient = False
            recommendation.missing_information = list(evaluation.reasons)
            recommendation.abstention_reason = ";".join(evaluation.reasons)
        elif not self._localize_recommendation(recommendation, response_language):
            recommendation.status = "abstained"
            recommendation.steps = []
            recommendation.total_estimated_days = None
            recommendation.evidence_sufficient = False
            recommendation.missing_information = ["response_translation_unavailable_or_unsafe"]
            recommendation.abstention_reason = "response_translation_unavailable_or_unsafe"
        logger.info(
            "procedural_recommendation_completed",
            correlation_id=correlation_id,
            procedure_type=recommendation.procedure_type,
            status=recommendation.status,
            step_count=len(recommendation.steps),
        )
        return recommendation