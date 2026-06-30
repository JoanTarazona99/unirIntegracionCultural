"""
RAG Service: wrapper around EnhancedRAGModule.

Encapsulates RAG logic with clean interface and structured error handling.
Does not modify the underlying module.

Limited to: search(), get_sources(), get_status()
TODO (Sprint 2): Add streaming support when conversation/cache layer is refactored.
"""

from typing import Dict, Optional

from app.config.logging_config import get_logger
from app.domain.exceptions import RAGError

logger = get_logger(__name__)


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
    
    def __init__(self, rag_module):
        """Initialize with an EnhancedRAGModule instance.
        
        Args:
            rag_module: EnhancedRAGModule instance from main.py
            
        Raises:
            RAGError: If module is not initialized
        """
        if rag_module is None:
            raise RAGError(
                "RAG module not initialized",
                context={"reason": "rag_module is None"}
            )
        self.rag_module = rag_module
        logger.info("rag_service_initialized", module_type=type(rag_module).__name__)
    
    def search(
        self,
        query: str,
        language: str = "es",
        context_type: str = "chat",
        session_id: Optional[str] = None
    ) -> Dict:
        """Search documents and generate response.
        
        Args:
            query: User query string
            language: Response language (ru, es, en, etc.)
            context_type: Context for RAG (chat, profile_*, etc.)
            session_id: Optional session ID for conversation history
            
        Returns:
            Dict with response, sources, and metadata
            
        Raises:
            RAGError: If search fails
        """
        try:
            logger.info(
                "rag_search_start",
                query_length=len(query),
                language=language,
                context_type=context_type
            )
            
            result = self.rag_module.search_and_generate(
                query=query,
                context_type=context_type,
                language=language,
                session_id=session_id
            )
            
            logger.info(
                "rag_search_success",
                sources_found=result.get("sources_found", 0),
                response_mode=result.get("response_mode")
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "rag_search_failed",
                error=str(e),
                query_sample=query[:50]
            )
            raise RAGError(
                f"RAG search failed: {str(e)}",
                context={"query": query[:100], "language": language}
            )
    
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
            
        except Exception as e:
            logger.error("rag_sources_failed", error=str(e))
            raise RAGError(
                f"Failed to get RAG sources: {str(e)}",
                context={"reason": "sources_retrieval"}
            )
    
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
            
        except Exception as e:
            logger.error("rag_status_check_failed", error=str(e))
            raise RAGError(
                f"Failed to get RAG status: {str(e)}",
                context={"reason": "status_retrieval"}
            )
