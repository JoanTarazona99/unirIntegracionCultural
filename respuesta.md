# SPRINT 1 DÍA 1 - VERSIÓN FINAL APLICABLE

## 1. ARCHIVOS NUEVOS

### backend/app/__init__.py

```python
"""
KubGU Assistant - Backend Application Package

Modular architecture with clear separation of concerns:
- config: Settings and logging configuration
- domain: Core domain models and exceptions
- middleware: FastAPI middleware components
"""

__version__ = "0.5.0"
__author__ = "KubGU Development Team"
```

---

### backend/app/config/__init__.py

```python
"""Configuration module.

Exports:
- settings: Pydantic Settings instance
- configure_logging: Logging initialization function
- get_logger: Logger factory
"""

from .settings import settings
from .logging_config import configure_logging, get_logger

__all__ = ["settings", "configure_logging", "get_logger"]
```

---

### backend/app/config/settings.py

```python
"""
Pydantic Settings for KubGU Assistant Backend.

Centralizes all configuration from environment variables.
Provides type-safe, validated settings with sensible defaults.

Usage:
    from app.config.settings import settings
    
    print(settings.app_name)
    print(settings.api_port)
    print(settings.cors_allowed_origins)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Priority order:
    1. .env file (if exists)
    2. Environment variables
    3. Default values
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # ==================== APPLICATION ====================
    app_name: str = Field(
        default="Asistente de Integración Cultural - KubGU",
        description="Application display name"
    )
    app_version: str = Field(
        default="0.5.0",
        description="Semantic version"
    )
    environment: str = Field(
        default="development",
        description="Environment: development, testing, production"
    )
    
    # ==================== API SERVER ====================
    api_host: str = Field(
        default="0.0.0.0",
        description="API host address"
    )
    api_port: int = Field(
        default=8000,
        description="API port"
    )
    debug: bool = Field(
        default=True,
        description="Enable debug mode"
    )
    
    # ==================== CORS ====================
    cors_allowed_origins: List[str] = Field(
        default=[
            "http://localhost:8000",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:3000",
        ],
        description="CORS allowed origins (explicit whitelist, no wildcards)"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    
    # ==================== RATE LIMITING ====================
    rate_limit_requests: int = Field(
        default=30,
        description="Max requests per time window"
    )
    rate_limit_window: int = Field(
        default=60,
        description="Rate limit window in seconds"
    )
    
    # ==================== CACHING ====================
    cache_max_entries: int = Field(
        default=500,
        description="Maximum entries in LRU cache"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache time-to-live in seconds (1 hour default)"
    )
    
    # ==================== LOGGING ====================
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    log_format: str = Field(
        default="json",
        description="Logging format: json or text"
    )
    
    # ==================== FEATURES ====================
    enable_tts: bool = Field(
        default=True,
        description="Enable Text-to-Speech (gTTS)"
    )
    enable_stt: bool = Field(
        default=True,
        description="Enable Speech-to-Text (Google Speech Recognition)"
    )
    enable_semantic_search: bool = Field(
        default=False,
        description="Enable semantic search (sentence-transformers)"
    )
    enable_llm: bool = Field(
        default=False,
        description="Enable LLM integration (Ollama)"
    )
    
    # ==================== VALIDATORS ====================
    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v):
        allowed = {"development", "testing", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v
    
    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v):
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if str(v).upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return str(v).upper()
    
    @field_validator("log_format", mode="before")
    @classmethod
    def validate_log_format(cls, v):
        allowed = {"json", "text"}
        if v not in allowed:
            raise ValueError(f"log_format must be one of {allowed}")
        return v


# Global settings instance
settings = Settings()
```

---

### backend/app/config/logging_config.py

```python
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
```

---

### backend/app/domain/__init__.py

```python
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
```

---

### backend/app/domain/exceptions.py

```python
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
```

---

### backend/app/middleware/__init__.py

```python
"""
Middleware module: FastAPI middleware components.

Contains:
- logging_middleware: Request/response logging with timing
"""

from .logging_middleware import LoggingMiddleware

__all__ = ["LoggingMiddleware"]
```

---

### backend/app/middleware/logging_middleware.py

```python
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
```

---

## 2. BLOQUES PARA backend/main.py

### BLOQUE 1 IMPORTS

Reemplazar líneas 1-16 con esto:

```python
import sys
import json
import os
import io
import uuid
import time
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, AsyncGenerator

# Add backend to path for app imports
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import settings
from app.config.logging_config import configure_logging, get_logger
from app.middleware.logging_middleware import LoggingMiddleware

from enhanced_rag import EnhancedRAGModule
from translator import create_translator
from personalization import get_conversation_memory, ConversationMemory
from cache_module import get_rag_cache, LRUCache, cache_rag_query, get_cached_rag_query
```

---

### BLOQUE 2 INIT FASTAPI + LOGGING

Reemplazar líneas 18-26 (FastAPI init) con esto:

```python
# ==================== APPLICATION INITIALIZATION ====================
configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Backend para soporte inteligente a estudiantes extranjeros",
    version=settings.app_version,
    debug=settings.debug
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

logger.info(
    "app_startup",
    app_name=settings.app_name,
    version=settings.app_version,
    environment=settings.environment
)

# Inicializar módulo RAG mejorado e traductor multiidioma
rag_module = EnhancedRAGModule()
translator = create_translator()

# Initialize conversation memory
conversation_memory = get_conversation_memory(max_history=10)
```

---

### BLOQUE 3 CACHE

Reemplazar línea ~48 con esto:

```python
# Initialize cache
cache = get_rag_cache(max_entries=settings.cache_max_entries, default_ttl=settings.cache_ttl_seconds)
```

---

### BLOQUE 4 TTS/STT

Reemplazar líneas ~52-62 con esto:

```python
# Check TTS/STT availability
TTS_AVAILABLE = False
STT_AVAILABLE = False
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
    logger.info("feature_enabled", service="TTS", provider="gTTS")
except ImportError:
    logger.warning("feature_disabled", service="TTS", reason="gTTS not installed")

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
    logger.info("feature_enabled", service="STT", provider="Google Speech Recognition")
except ImportError:
    logger.warning("feature_disabled", service="STT", reason="SpeechRecognition not installed")
```

---

### BLOQUE 5 RATE LIMITER INIT

Reemplazar línea ~75 (y el siguiente bloque) con esto:

```python
rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)

logger.info(
    "rate_limiter_initialized",
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)
```

---

### BLOQUE 6 CORS

Reemplazar líneas ~108-118 (CORS middleware y funciones auxiliares) con esto:

```python
# ==================== CORS ====================
# CORS middleware - use explicit whitelist from settings (NO wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

logger.info(
    "cors_configured",
    allowed_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials
)
```

---

### BLOQUE 7 MAIN

Reemplazar línea ~955 (if __name__ == "__main__") con esto:

```python
if __name__ == "__main__":
    import uvicorn
    
    logger.info(
        "starting_uvicorn",
        host=settings.api_host,
        port=settings.api_port,
        environment=settings.environment
    )
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_config=None
    )
```

---

## 3. DEPENDENCIAS

### requirements.txt

Agregar estas líneas (al final o después de pydantic):

```
structlog==23.2.0
pydantic-settings==2.1.0
```

### backend/requirements-dev.txt

Sin cambios en backend/requirements-dev.txt

---

## 4. COMANDOS

```bash
# 1. Crear directorios
mkdir -p backend/app/config backend/app/domain backend/app/middleware

# 2. Crear los 8 archivos nuevos (copiar contenido de sección 1)

# 3. Aplicar los 7 bloques a backend/main.py (sección 2)

# 4. Actualizar requirements.txt (sección 3)

# 5. Instalar dependencias
cd backend
pip install -r ../requirements.txt

# 6. Probar imports
python -c "from app.config.settings import settings; print('✓ Settings OK'); print(f'  app_name: {settings.app_name}')"
python -c "from app.config.logging_config import configure_logging, get_logger; configure_logging(); logger = get_logger(__name__); logger.info('test'); print('✓ Logging OK')"
python -c "from app.domain.exceptions import AppError, RAGError, TranslationError, ValidationError; print('✓ Exceptions OK')"
python -c "from app.middleware.logging_middleware import LoggingMiddleware; print('✓ Middleware OK')"

# 7. Ejecutar backend
python main.py

# Esperado: logs en JSON, no print()
```
