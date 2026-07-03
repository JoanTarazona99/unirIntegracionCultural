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
        default=8080,
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
            "http://localhost:8001",
            "http://localhost:8080",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
            "http://127.0.0.1:8080",
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
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama server host URL (used when enable_llm is True)"
    )
    ollama_model: str = Field(
        default="qwen2.5:7b-instruct-q4_K_M",
        description="Ollama model name (qwen2.5:7b-instruct-q4_K_M, qwen3:8b-q4_K_M, etc)"
    )

    # ==================== RETRIEVAL (RAG) ====================
    retrieval_mode: str = Field(
        default="keyword",
        description="Retrieval strategy: keyword | bm25 | dense | hybrid | hybrid_rerank",
    )
    dense_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="Sentence-transformers model for dense retrieval",
    )
    reranker_model: str = Field(
        default="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        description="Cross-encoder model used when retrieval_mode=hybrid_rerank",
    )
    enable_reranker: bool = Field(
        default=False,
        description="Enable cross-encoder reranking (requires sentence-transformers, CPU-heavy)",
    )
    rrf_k: int = Field(
        default=60,
        description="Reciprocal Rank Fusion constant (higher = flatter fusion)",
    )
    retrieval_top_k: int = Field(
        default=5,
        description="Number of chunks returned by the retriever",
    )

    # ==================== TRUSTWORTHY AI ====================
    enable_citation_guard: bool = Field(
        default=False,
        description="Require answers to be grounded in retrieved sources; abstain otherwise",
    )
    abstention_threshold: float = Field(
        default=0.35,
        description="Minimum grounding/faithfulness score below which the assistant abstains",
    )

    @field_validator("retrieval_mode")
    @classmethod
    def _validate_retrieval_mode(cls, value: str) -> str:
        allowed = {"keyword", "bm25", "dense", "hybrid", "hybrid_rerank"}
        normalized = (value or "keyword").strip().lower()
        if normalized not in allowed:
            raise ValueError(
                f"retrieval_mode must be one of {sorted(allowed)}, got '{value}'"
            )
        return normalized

    # ==================== TELEGRAM BOT ====================
    telegram_bot_token: str = Field(
        default="",
        description="Telegram bot token (required only when running the Telegram bot)"
    )
    
    # ==================== PERSISTENCE - REDIS ====================
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL (optional, falls back to LRU if unavailable)"
    )
    enable_redis: bool = Field(
        default=False,
        description="Enable Redis cache (auto-fallback to LRU if not available)"
    )
    
    # ==================== PERSISTENCE - DATABASE ====================
    database_url: str = Field(
        default="sqlite:///./data/assistant.db",
        description="Database URL (SQLite or PostgreSQL, auto-fallback to memory)"
    )
    enable_database: bool = Field(
        default=False,
        description="Enable database persistence (auto-fallback to memory if not available)"
    )
    db_path: str = Field(
        default="./data/assistant.db",
        description="Path to SQLite database file (if using SQLite)"
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
