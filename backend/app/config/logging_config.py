"""
Structured logging configuration using structlog.

Provides:
- Automatic JSON output with timestamps
- Request ID tracking (for middleware integration)
- Automatic exception formatting

Usage:
    from app.config.logging_config import configure_logging, get_logger
    
    configure_logging()
    logger = get_logger(__name__)
    
    logger.info("message", key="value", status="ok")
"""

import structlog
import logging
from .settings import settings


def configure_logging() -> None:
    """
    Configure structured logging with structlog.
    
    Sets up JSON output with automatic timestamps and context propagation.
    Should be called once at application startup.
    """
    
    # Determine if JSON or text format
    is_json = settings.log_format == "json"
    
    structlog.configure(
        processors=[
            # Filter by log level before processing
            structlog.stdlib.filter_by_level,
            
            # Add log level and timestamp
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            
            # Add context variables
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            
            # JSON or text rendering
            structlog.processors.JSONRenderer() if is_json else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure Python's logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level),
        handlers=[
            logging.StreamHandler(),
        ]
    )


def get_logger(name: str = __name__):
    """
    Get a structlog logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
