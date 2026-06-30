"""
Custom exception hierarchy for KubGU Assistant.

Provides semantic exceptions for different failure modes:
- AppError: Base exception for all app-level errors
- RAGError: RAG search/generation failures
- TranslationError: Translation service failures
- ValidationError: Input validation failures
"""


class AppError(Exception):
    """
    Base exception for all application-level errors.
    
    Includes optional error code and context for structured logging.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        context: dict = None,
        original_exception: Exception = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.original_exception = original_exception
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Serialize exception to dict for logging."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
        }


class RAGError(AppError):
    """
    Raised when RAG search or generation fails.
    
    Common causes:
    - Document library unavailable
    - LLM service timeout
    - Semantic search model not loaded
    - Invalid query format
    """
    
    def __init__(self, message: str, context: dict = None, original_exception: Exception = None):
        super().__init__(
            message=message,
            error_code="RAG_ERROR",
            context=context,
            original_exception=original_exception
        )


class TranslationError(AppError):
    """
    Raised when translation service fails.
    
    Common causes:
    - Target language not supported
    - Translation API unavailable
    - Text encoding issues
    """
    
    def __init__(self, message: str, context: dict = None, original_exception: Exception = None):
        super().__init__(
            message=message,
            error_code="TRANSLATION_ERROR",
            context=context,
            original_exception=original_exception
        )


class ValidationError(AppError):
    """
    Raised when input validation fails.
    
    Common causes:
    - Missing required fields
    - Invalid data types
    - Value out of range
    - Invalid format
    """
    
    def __init__(self, message: str, field: str = None, context: dict = None):
        ctx = context or {}
        if field:
            ctx["field"] = field
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            context=ctx
        )
