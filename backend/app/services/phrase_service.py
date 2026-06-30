"""
Phrase Service: wrapper around phrases database (JSON).

Encapsulates phrase management logic with clean interface and error handling.
Does not modify the underlying data storage.
"""

from typing import Dict, List, Optional

from app.config.logging_config import get_logger
from app.domain.exceptions import ValidationError, AppError

logger = get_logger(__name__)


class PhraseService:
    """Service for phrase operations.
    
    Wraps phrase database access without modifying it.
    Handles errors with custom exceptions.
    Provides clean interface for routers.
    """
    
    def __init__(self, phrases_db: List[Dict]):
        """Initialize with phrases database list.
        
        Args:
            phrases_db: List of phrase dictionaries from main.py
            
        Raises:
            ValidationError: If database is invalid
        """
        if phrases_db is None or not isinstance(phrases_db, list):
            raise ValidationError(
                "Phrases database not initialized or invalid",
                field="phrases_db"
            )
        
        self.phrases_db = phrases_db
        self._categories = self._extract_categories()
        
        logger.info(
            "phrase_service_initialized",
            total_phrases=len(self.phrases_db),
            categories=len(self._categories)
        )
    
    def _extract_categories(self) -> set:
        """Extract unique categories from phrases."""
        return set(
            phrase.get("category")
            for phrase in self.phrases_db
            if "category" in phrase
        )
    
    def list_phrases(
        self,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """List phrases with optional category filter.
        
        Args:
            category: Optional category to filter by
            limit: Maximum number of phrases to return
            
        Returns:
            List of phrase dictionaries
            
        Raises:
            ValidationError: If parameters are invalid
            AppError: If operation fails
        """
        try:
            if limit < 1 or limit > 100:
                raise ValidationError(
                    "Limit must be between 1 and 100",
                    field="limit"
                )
            
            logger.info(
                "list_phrases_start",
                category=category,
                limit=limit
            )
            
            # Filter by category if provided
            if category:
                if category not in self._categories:
                    logger.warning("category_not_found", category=category)
                    return []
                
                filtered = [
                    p for p in self.phrases_db
                    if p.get("category") == category
                ]
            else:
                filtered = self.phrases_db
            
            # Return limited result
            result = filtered[:limit]
            
            logger.info(
                "list_phrases_success",
                returned=len(result),
                category=category
            )
            
            return result
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "list_phrases_failed",
                error=str(e),
                category=category
            )
            raise AppError(
                f"Failed to list phrases: {str(e)}",
                error_code="LIST_PHRASES_ERROR",
                context={"category": category}
            )
    
    def get_phrase(self, phrase_id: int) -> Optional[Dict]:
        """Get a single phrase by ID.
        
        Args:
            phrase_id: ID of the phrase to retrieve
            
        Returns:
            Phrase dictionary or None if not found
            
        Raises:
            ValidationError: If phrase_id is invalid
            AppError: If operation fails
        """
        try:
            if not isinstance(phrase_id, int) or phrase_id < 1:
                raise ValidationError(
                    "phrase_id must be a positive integer",
                    field="phrase_id"
                )
            
            logger.info("get_phrase_start", phrase_id=phrase_id)
            
            # Find phrase by ID
            for phrase in self.phrases_db:
                if phrase.get("id") == phrase_id:
                    logger.info("get_phrase_success", phrase_id=phrase_id)
                    return phrase
            
            logger.warning("phrase_not_found", phrase_id=phrase_id)
            return None
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("get_phrase_failed", error=str(e), phrase_id=phrase_id)
            raise AppError(
                f"Failed to get phrase: {str(e)}",
                error_code="GET_PHRASE_ERROR",
                context={"phrase_id": phrase_id}
            )
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search phrases by text query.
        
        Args:
            query: Search query string
            limit: Maximum results
            
        Returns:
            List of matching phrases
            
        Raises:
            ValidationError: If query is invalid
            AppError: If operation fails
        """
        try:
            if not query or not isinstance(query, str):
                raise ValidationError(
                    "Query must be a non-empty string",
                    field="query"
                )
            
            query_lower = query.lower()
            
            logger.info("search_phrases_start", query=query, limit=limit)
            
            results = []
            for phrase in self.phrases_db:
                if (query_lower in phrase.get("russian", "").lower() or
                    query_lower in phrase.get("english", "").lower() or
                    query_lower in phrase.get("transliteration", "").lower()):
                    results.append(phrase)
            
            # Limit results
            result = results[:limit]
            
            logger.info("search_phrases_success", found=len(result), query=query)
            
            return result
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("search_phrases_failed", error=str(e), query=query)
            raise AppError(
                f"Failed to search phrases: {str(e)}",
                error_code="SEARCH_PHRASES_ERROR",
                context={"query": query}
            )
    
    def get_status(self) -> Dict:
        """Get phrase service status.
        
        Returns:
            Dict with service status and statistics
        """
        try:
            return {
                "available": True,
                "total_phrases": len(self.phrases_db),
                "categories": list(self._categories),
                "category_count": len(self._categories)
            }
        except Exception as e:
            logger.error("phrase_status_failed", error=str(e))
            return {
                "available": False,
                "error": str(e)
            }
