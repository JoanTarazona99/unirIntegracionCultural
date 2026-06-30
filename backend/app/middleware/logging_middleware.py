"""
Logging middleware for FastAPI.

Logs all HTTP requests and responses with:
- HTTP method and path
- Response status code
- Request duration (milliseconds)
- Request ID (for tracing)

Usage:
    from app.middleware.logging_middleware import LoggingMiddleware
    
    app.add_middleware(LoggingMiddleware)
"""

import time
import uuid
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Lazy import to avoid circular dependencies
_logger = None

def get_logger():
    """Get logger instance with fallback to standard logging."""
    global _logger
    if _logger is not None:
        return _logger
    
    try:
        from app.config.logging_config import get_logger as get_structlog
        _logger = get_structlog(__name__)
    except ImportError:
        # Fallback to standard Python logging
        _logger = logging.getLogger(__name__)
    
    return _logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware that logs all requests and responses.
    
    Attributes logged:
    - request_id: UUID for request tracing
    - method: HTTP method (GET, POST, etc.)
    - path: Request path
    - status_code: Response HTTP status code
    - duration_ms: Request duration in milliseconds
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with logging."""
        
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        request.scope["request_id"] = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract basic request info
        method = request.method
        path = request.url.path
        
        logger = get_logger()
        
        try:
            # Call next middleware/route handler
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log the request/response
            logger.info(
                "http_request",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            # Add request ID to response headers for tracing
            response.headers["X-Request-ID"] = request_id
            
            return response
        
        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log the error
            logger.error(
                "http_request_failed",
                request_id=request_id,
                method=method,
                path=path,
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            
            # Re-raise to let FastAPI's exception handlers deal with it
            raise
