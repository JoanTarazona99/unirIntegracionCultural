"""
Domain module: Core business logic and exceptions.

Contains:
- exceptions: Custom exception hierarchy
"""

from .exceptions import AppError, RAGError, TranslationError, ValidationError

__all__ = [
    "AppError",
    "RAGError", 
    "TranslationError",
    "ValidationError",
]
