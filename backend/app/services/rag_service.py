"""
RAG Service: wrapper around EnhancedRAGModule.

Encapsulates RAG logic with clean interface and structured error handling.
Does not modify the underlying module.

    Limited to: search(), retrieve_evidence(), get_sources(), get_status()
TODO (Sprint 2): Add streaming support when conversation/cache layer is refactored.
"""

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from app.config.logging_config import get_logger
from app.config.settings import settings
from app.domain.exceptions import RAGError
from app.api.models import EVIDENCE_LANGUAGES
from app.services.triage_service import TriageService
from procedural.language import ProcedureLanguageRouter
from retrieval.base import RetrievalResult
from retrieval.fusion import weighted_reciprocal_rank_fusion

logger = get_logger(__name__)


ADAPTIVE_CHANNEL_WEIGHTS = {
    "dense_original": 1.0,
    "bm25_original": 0.8,
    "dense_ru_translated": 0.9,
    "dense_es_translated": 0.6,
    "dense_en_translated": 0.6,
}


def weighted_rrf(
    results_by_channel: Mapping[str, List[RetrievalResult]],
    weights: Mapping[str, float] = ADAPTIVE_CHANNEL_WEIGHTS,
    *,
    k: int = 60,
    top_k: Optional[int] = None,
) -> List[RetrievalResult]:
    """Compatibility wrapper around the retrieval-layer weighted RRF."""
    return weighted_reciprocal_rank_fusion(
        results_by_channel,
        weights,
        k=k,
        top_k=top_k,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _environment_flag(name: str, configured: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return configured
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _development_environment() -> bool:
    return os.environ.get("ENVIRONMENT", settings.environment).strip().lower() == "development"


def _raw_query_logging_enabled() -> bool:
    return _development_environment() and _environment_flag(
        "LOG_RAW_QUERIES", getattr(settings, "log_raw_queries", False)
    )


def _raw_payload_logging_enabled() -> bool:
    return _raw_query_logging_enabled() and _environment_flag(
        "LOG_RAW_RAG_PAYLOADS", getattr(settings, "log_raw_rag_payloads", False)
    )


def _text_metadata(prefix: str, value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    return {
        f"{prefix}_sha256": _sha256(value),
        f"{prefix}_length": len(value),
    }


def _query_log_metadata(query: str, correlation_id: Optional[str]) -> Dict[str, Any]:
    raw_query_logged = _raw_query_logging_enabled()
    metadata = {
        "query_sha256": _sha256(query),
        "query_length": len(query),
        "correlation_id": correlation_id,
        "request_id": correlation_id,
        "raw_payload_logged": raw_query_logged,
        "privacy_mode": "development_raw_query" if raw_query_logged else "redacted",
    }
    if raw_query_logged:
        metadata["query"] = query
    return metadata


class RAGService:
    """Service for RAG operations.
    
    Wraps EnhancedRAGModule without modifying it.
    Handles errors with RAGError exceptions.
    Provides clean interface for routers.
    
    Scope (Sprint 1 Day 3):
    - search(): Query documents and generate response
    - get_sources(): List available sources
    - get_status(): System status
    
    Not included yet:
    - Streaming (requires conversation/cache refactor)
    """
    
    def __init__(
        self,
        rag_module=None,
        *,
        project_root: Optional[Path] = None,
        use_llm: bool = True,
        translator=None,
        triage_service: Optional[TriageService] = None,
    ):
        """Initialize with an EnhancedRAGModule instance.
        
        Args:
            rag_module: EnhancedRAGModule instance from main.py
            project_root: Optional isolated state root used to create a new module
            use_llm: Whether the newly created module should enable its LLM
            
        Raises:
            RAGError: If module is not initialized
        """
        if rag_module is None and project_root is not None:
            from enhanced_rag import EnhancedRAGModule

            rag_module = EnhancedRAGModule(
                use_llm=use_llm,
                project_root=project_root,
            )
        if rag_module is None:
            raise RAGError(
                "RAG module not initialized",
                context={"reason": "rag_module is None"}
            )
        self.rag_module = rag_module
        self.translator = translator
        self.triage_service = triage_service or TriageService()
        self.language_router = ProcedureLanguageRouter()
        logger.info("rag_service_initialized", module_type=type(rag_module).__name__)

    def _translate_adaptive_query(
        self,
        query: str,
        *,
        source_language: str,
        target_language: str,
        expected_procedure_type: str,
        correlation_id: Optional[str],
    ) -> Optional[str]:
        translated, _ = self.language_router.translate_checked(
            query,
            source_language=source_language,
            target_language=target_language,
            translator=self.translator,
        )
        if translated is None:
            logger.warning(
                "adaptive_query_translation_rejected",
                source_language=source_language,
                target_language=target_language,
                correlation_id=correlation_id,
                query_sha256=_sha256(query),
                reason="unavailable_or_critical_information_changed",
            )
            return None

        translated_triage = self.triage_service.classify_procedure_type(
            translated,
            target_language,
        )
        if translated_triage["procedure_type"] != expected_procedure_type:
            logger.warning(
                "adaptive_query_translation_rejected",
                source_language=source_language,
                target_language=target_language,
                correlation_id=correlation_id,
                query_sha256=_sha256(query),
                translated_query_sha256=_sha256(translated),
                reason="procedure_intent_changed",
            )
            return None
        return translated

    def _adaptive_snapshot(
        self,
        channels: Dict[str, List[RetrievalResult]],
        query_variants: List[str],
    ) -> tuple[List[RetrievalResult], Dict, List[Dict]]:
        fused = self.rag_module.fuse_adaptive_channels(
            channels,
            weights=ADAPTIVE_CHANNEL_WEIGHTS,
            top_k=settings.retrieval_top_k,
        )
        assessment = self.rag_module.evaluate_adaptive_evidence(
            query_variants,
            fused,
        )
        rendered = self.rag_module.render_adaptive_results(fused)
        return fused, assessment, rendered

    def retrieve_evidence_adaptive(
        self,
        query: str,
        language: str,
        *,
        correlation_id: Optional[str] = None,
    ) -> Dict:
        """Run evidence-driven multilingual fallback with at most three translations."""
        started = time.perf_counter()
        triage = self.triage_service.classify_procedure_type(query, language)
        channels: Dict[str, List[RetrievalResult]] = {}
        query_variants = [query]
        translations: Dict[str, str] = {}
        translation_failures: List[str] = []

        level_one = self.rag_module.retrieve_adaptive_channels(query, language)
        channels.update(level_one["channels"])
        _, assessment, rendered = self._adaptive_snapshot(channels, query_variants)
        completed_level = 1

        if not assessment.get("sufficient", False):
            primary = triage["primary_target"]
            if primary != language:
                translated = self._translate_adaptive_query(
                    query,
                    source_language=language,
                    target_language=primary,
                    expected_procedure_type=triage["procedure_type"],
                    correlation_id=correlation_id,
                )
                if translated is not None:
                    translations[primary] = translated
                    query_variants.append(translated)
                    level_two = self.rag_module.retrieve_adaptive_channels(
                        query,
                        language,
                        translated_queries={primary: translated},
                    )
                    channels.update(level_two["channels"])
                    _, assessment, rendered = self._adaptive_snapshot(
                        channels,
                        query_variants,
                    )
                else:
                    translation_failures.append(primary)
            completed_level = 2

        if not assessment.get("sufficient", False):
            remaining_targets = [
                target
                for target in EVIDENCE_LANGUAGES
                if target != language and target not in translations
            ]

            def translate_target(target_language: str):
                return target_language, self._translate_adaptive_query(
                    query,
                    source_language=language,
                    target_language=target_language,
                    expected_procedure_type=triage["procedure_type"],
                    correlation_id=correlation_id,
                )

            if remaining_targets:
                with ThreadPoolExecutor(max_workers=len(remaining_targets)) as executor:
                    for target, translated in executor.map(
                        translate_target,
                        remaining_targets,
                    ):
                        if translated is None:
                            translation_failures.append(target)
                        else:
                            translations[target] = translated
                            query_variants.append(translated)
                if translations:
                    level_three = self.rag_module.retrieve_adaptive_channels(
                        query,
                        language,
                        translated_queries=translations,
                    )
                    channels.update(level_three["channels"])
                    _, assessment, rendered = self._adaptive_snapshot(
                        channels,
                        query_variants,
                    )
            completed_level = 3

        sufficient = bool(assessment.get("sufficient", False))
        abstention_reason = None if sufficient else "insufficient_multilingual_evidence"
        return {
            "results": rendered,
            "search_mode": "adaptive_weighted_rrf",
            "evidence_assessment": assessment,
            "adaptive_retrieval": {
                "completed_level": completed_level if sufficient else 4,
                "channels": list(channels),
                "triage": triage,
                "translated_targets": list(translations),
                "translation_failures": sorted(set(translation_failures)),
                "dense_available": level_one.get("dense_available", False),
                "bm25_available": level_one.get("bm25_available", False),
                "abstention_reason": abstention_reason,
                "latency_ms": round((time.perf_counter() - started) * 1000.0, 1),
            },
        }
    
    def search(
        self,
        query: str,
        language: str = "es",
        context_type: str = "chat",
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict:
        """Search documents and generate response.
        
        Args:
            query: User query string
            language: Response language (ru, es, en, etc.)
            context_type: Context for RAG (chat, profile_*, etc.)
            session_id: Optional session ID for conversation history
            correlation_id: Request identifier for acquisition-event tracing
            
        Returns:
            Dict with response, sources, and metadata
            
        Raises:
            RAGError: If search fails
        """
        query_metadata = _query_log_metadata(query, correlation_id)
        try:
            logger.info(
                "rag_search_start",
                language=language,
                context_type=context_type,
                **query_metadata,
            )
            
            adaptive = None
            if hasattr(self.rag_module, "retrieve_adaptive_channels"):
                try:
                    adaptive = self.retrieve_evidence_adaptive(
                        query,
                        language,
                        correlation_id=correlation_id,
                    )
                except Exception as adaptive_error:
                    logger.warning(
                        "adaptive_retrieval_fallback",
                        reason="adaptive_error",
                        error_type=type(adaptive_error).__name__,
                        **query_metadata,
                    )

            adaptive_metadata = (adaptive or {}).get("adaptive_retrieval", {})
            use_adaptive = bool(
                adaptive
                and adaptive.get("results")
                and adaptive_metadata.get("dense_available")
            )
            if use_adaptive:
                result = self.rag_module.search_and_generate(
                    query=query,
                    context_type=context_type,
                    language=language,
                    session_id=session_id,
                    correlation_id=correlation_id,
                    retrieved_results=adaptive["results"],
                    retrieval_mode_override="adaptive_weighted_rrf",
                    evidence_query=adaptive.get("evidence_assessment", {}).get(
                        "assessment_query"
                    ),
                    allow_external=False,
                )
                result["adaptive_retrieval"] = adaptive_metadata
            else:
                result = self.rag_module.search_and_generate(
                    query=query,
                    context_type=context_type,
                    language=language,
                    session_id=session_id,
                    correlation_id=correlation_id,
                )
                if adaptive is not None:
                    result["adaptive_retrieval"] = {
                        **adaptive_metadata,
                        "legacy_fallback": True,
                        "legacy_fallback_reason": "dense_unavailable_or_empty",
                    }
            
            response = result.get("response")
            success_metadata = {
                **query_metadata,
                **_text_metadata("response", response),
                "result_count": result.get("sources_found", 0),
                "chunk_count": len(result.get("sources", [])),
                "source_count": len(result.get("sources", [])),
            }
            raw_payload_logged = _raw_payload_logging_enabled()
            success_metadata["raw_payload_logged"] = raw_payload_logged
            success_metadata["privacy_mode"] = (
                "development_raw" if raw_payload_logged else query_metadata["privacy_mode"]
            )
            if raw_payload_logged:
                success_metadata["response"] = response
                success_metadata["chunks"] = [
                    source.get("content", "")
                    for source in result.get("sources", [])
                    if isinstance(source, dict)
                ]

            logger.info(
                "rag_search_success",
                sources_found=result.get("sources_found", 0),
                response_mode=result.get("response_mode"),
                **success_metadata,
            )
            
            return result
            
        except Exception as error:
            error_metadata = {
                **query_metadata,
                "error_type": type(error).__name__,
                **_text_metadata("response", getattr(error, "response", None)),
                **_text_metadata("context", getattr(error, "context", None)),
            }
            raw_payload_logged = _raw_payload_logging_enabled()
            error_metadata["raw_payload_logged"] = raw_payload_logged
            if raw_payload_logged:
                if getattr(error, "response", None) is not None:
                    error_metadata["response"] = error.response
                if getattr(error, "context", None) is not None:
                    error_metadata["raw_context"] = error.context
            logger.error(
                "rag_search_failed",
                **error_metadata,
            )
            raise RAGError(
                "RAG search failed",
                context={
                    **error_metadata,
                    "language": language,
                },
            ) from None

    def retrieve_evidence(
        self,
        query: str,
        *,
        correlation_id: Optional[str] = None,
    ) -> Dict:
        """Retrieve source chunks without generation or external acquisition."""
        query_metadata = _query_log_metadata(query, correlation_id)
        try:
            result = self.rag_module.retrieve_evidence(query)
            logger.info(
                "rag_evidence_retrieved",
                result_count=len(result.get("results", [])),
                search_mode=result.get("search_mode"),
                evidence_sufficient=(
                    result.get("evidence_assessment", {}).get("sufficient", False)
                ),
                **query_metadata,
            )
            return result
        except Exception as error:
            logger.error(
                "rag_evidence_retrieval_failed",
                error_type=type(error).__name__,
                **query_metadata,
            )
            raise RAGError(
                "RAG evidence retrieval failed",
                context={"error_type": type(error).__name__},
            ) from None
    
    def get_sources(self) -> Dict:
        """Get available RAG sources.
        
        Returns:
            Dict with sources list and search mode
            
        Raises:
            RAGError: If retrieval fails
        """
        try:
            logger.info("rag_sources_requested")
            
            sources_list = self.rag_module.document_library.list_sources()
            search_mode = self.rag_module.document_library.get_search_mode()
            
            logger.info("rag_sources_retrieved", count=len(sources_list))
            
            return {
                "sources": sources_list,
                "search_mode": search_mode,
                "description": "Fuentes de documentos oficiales integradas"
            }
            
        except Exception as error:
            logger.error("rag_sources_failed", error_type=type(error).__name__)
            raise RAGError(
                "Failed to get RAG sources",
                context={
                    "reason": "sources_retrieval",
                    "error_type": type(error).__name__,
                },
            ) from None
    
    def get_status(self) -> Dict:
        """Get RAG module status.
        
        Returns:
            Dict with RAG status and capabilities
            
        Raises:
            RAGError: If status check fails
        """
        try:
            logger.info("rag_status_check")
            
            semantic_available = (
                hasattr(self.rag_module.document_library, '_use_semantic') and 
                self.rag_module.document_library._use_semantic
            )
            
            llm_enabled = (
                hasattr(self.rag_module, 'is_llm_enabled') and 
                self.rag_module.is_llm_enabled()
            )
            
            return {
                "available": True,
                "mode": self.rag_module.document_library.get_search_mode(),
                "sources": len(self.rag_module.document_library.documents) if hasattr(
                    self.rag_module, 'document_library'
                ) else 0,
                "semantic_search": semantic_available,
                "llm_enabled": llm_enabled
            }
            
        except Exception as error:
            logger.error("rag_status_check_failed", error_type=type(error).__name__)
            raise RAGError(
                "Failed to get RAG status",
                context={
                    "reason": "status_retrieval",
                    "error_type": type(error).__name__,
                },
            ) from None
