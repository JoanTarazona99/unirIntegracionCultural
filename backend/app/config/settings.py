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
