"""
System metrics routes for AI-transparency dashboard.

Exposes runtime metrics of the RAG/LLM stack: active models, retrieval mode,
cache efficiency, conversation load and trust configuration. All values are
read from live services (no simulated data).
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_rag_module,
    get_cache,
    get_conversation_memory,
    get_tts_available,
    get_stt_available,
)
from app.config.settings import settings

router = APIRouter()


@router.get("/api/metrics/system")
async def get_system_metrics():
    """Return live AI/ML system metrics for the academic dashboard."""
    rag_module = get_rag_module()
    cache = get_cache()
    conversation_memory = get_conversation_memory()

    # ---- LLM ----
    llm_available = (
        rag_module.is_llm_enabled() if hasattr(rag_module, "is_llm_enabled") else False
    )
    llm_model = None
    if llm_available and getattr(rag_module, "llm", None):
        llm_model = rag_module.llm.model

    # ---- Retrieval configuration ----
    retrieval_config = getattr(rag_module, "_retrieval_config", {}) or {}
    retrieval_mode = retrieval_config.get("mode", getattr(settings, "retrieval_mode", "keyword"))
    uses_dense = retrieval_mode in ("dense", "hybrid", "hybrid_rerank")
    uses_reranker = retrieval_mode == "hybrid_rerank"

    # ---- Cache efficiency ----
    cache_stats = cache.get_stats()

    # ---- Knowledge base size ----
    try:
        sources = rag_module.document_library.list_sources()
        num_sources = len(sources)
    except Exception:
        sources = []
        num_sources = 0

    return {
        "timestamp": datetime.now().isoformat(),
        "pipeline": {
            "retrieval_mode": retrieval_mode,
            "search_mode": rag_module.document_library.get_search_mode()
            if hasattr(rag_module.document_library, "get_search_mode")
            else retrieval_mode,
            "top_k": retrieval_config.get("top_k", getattr(settings, "retrieval_top_k", 5)),
            "rrf_k": retrieval_config.get("rrf_k", getattr(settings, "rrf_k", 60)),
            "citation_guard": retrieval_config.get(
                "citation_guard", getattr(settings, "enable_citation_guard", False)
            ),
            "abstention_threshold": retrieval_config.get(
                "abstention_threshold", getattr(settings, "abstention_threshold", 0.35)
            ),
        },
        "models": {
            "llm": {
                "name": llm_model,
                "provider": "ollama" if llm_available else None,
                "available": llm_available,
            },
            "embedding": {
                "name": retrieval_config.get(
                    "dense_model", getattr(settings, "dense_model", None)
                )
                if uses_dense
                else None,
                "active": uses_dense,
            },
            "reranker": {
                "name": retrieval_config.get(
                    "reranker_model", getattr(settings, "reranker_model", None)
                )
                if uses_reranker
                else None,
                "active": uses_reranker,
            },
        },
        "cache": {
            "entries": cache_stats.get("entries", 0),
            "hits": cache_stats.get("hits", 0),
            "misses": cache_stats.get("misses", 0),
            "hit_rate_percent": cache_stats.get("hit_rate_percent", 0),
        },
        "conversation": {
            "active_sessions": conversation_memory.get_session_count(),
            "max_history": 10,
        },
        "knowledge_base": {
            "sources": num_sources,
            "source_names": [s.get("name") if isinstance(s, dict) else s for s in sources],
        },
        "features": {
            "llm": llm_available,
            "tts": get_tts_available(),
            "stt": get_stt_available(),
            "dense_retrieval": uses_dense,
            "reranker": uses_reranker,
            "citation_guard": retrieval_config.get(
                "citation_guard", getattr(settings, "enable_citation_guard", False)
            ),
        },
    }
