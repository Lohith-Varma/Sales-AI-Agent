"""Validated, environment-driven application settings.

Settings are instantiated by the dependency container rather than at import time.
This makes configuration failures explicit during application startup and keeps
unit tests able to construct isolated settings instances.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    """Supported application log renderers."""

    JSON = "json"
    CONSOLE = "console"


class ConversationStoreBackend(StrEnum):
    """Supported conversation persistence implementations."""

    MEMORY = "memory"


Port = Annotated[int, Field(ge=1, le=65_535)]
PositiveSeconds = Annotated[float, Field(gt=0)]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]
PositiveInteger = Annotated[int, Field(gt=0)]


class Settings(BaseSettings):
    """Immutable runtime configuration loaded from environment variables.

    Field names intentionally mirror the documented environment variables after
    case normalization. Comma-separated settings are normalized into immutable
    tuples by validators.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
        validate_default=True,
        enable_decoding=False,
    )

    # Application
    app_name: str = "Pay-in-3 AI Voice Sales Co-Pilot"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_host: str = "0.0.0.0"
    app_port: Port = 8000
    app_debug: bool = False
    app_version: str = "0.1.0"
    allowed_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://localhost:5173",
    )
    max_concurrent_sessions: PositiveInteger = 25
    auth_required: bool = False
    jwt_secret: SecretStr | None = None

    # Core CRM integration. Set CORE_API_URL empty for isolated AI-only runs.
    core_api_url: str | None = "http://127.0.0.1:8001"
    internal_api_key: SecretStr | None = None
    core_persistence_timeout_seconds: PositiveSeconds = 2.0
    core_persistence_max_retries: Annotated[int, Field(ge=0, le=5)] = 2

    # Logging and observability
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.JSON
    log_redact_sensitive_values: bool = True
    service_instance_id: str = "local"

    # Gemini
    gemini_api_key: SecretStr
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_request_timeout_seconds: PositiveSeconds = 20
    gemini_max_retries: Annotated[int, Field(ge=0, le=5)] = 2
    gemini_analysis_temperature: Probability = 0.0
    gemini_response_temperature: Probability = 0.2

    # Whisper and audio
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str | None = "en"
    audio_sample_rate_hz: Annotated[int, Field(ge=8_000, le=48_000)] = 16_000
    audio_channels: Annotated[int, Field(ge=1, le=2)] = 1
    audio_sample_width_bytes: Annotated[int, Field(ge=1, le=4)] = 2
    audio_chunk_duration_ms: Annotated[int, Field(ge=20, le=1_000)] = 100
    transcription_window_seconds: Annotated[float, Field(ge=0.5, le=30)] = 3.0
    max_audio_buffer_seconds: Annotated[float, Field(ge=1, le=120)] = 15.0
    max_websocket_message_bytes: Annotated[int, Field(ge=1_024, le=10_485_760)] = 262_144

    # Embeddings and ChromaDB
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: Annotated[int, Field(ge=1, le=1_024)] = 32
    normalize_embeddings: bool = True
    chroma_persist_directory: Path = Path("data/chroma")
    chroma_collection: str = "pay_in_3_knowledge"
    anonymized_telemetry: bool = False

    # Document ingestion and retrieval
    knowledge_document_directory: Path = Path("data/documents")
    supported_document_extensions: tuple[str, ...] = (".pdf", ".txt", ".md", ".json")
    document_chunk_size: Annotated[int, Field(ge=200, le=8_000)] = 900
    document_chunk_overlap: Annotated[int, Field(ge=0, le=2_000)] = 150
    rag_top_k: Annotated[int, Field(ge=1, le=50)] = 5
    rag_fetch_k: Annotated[int, Field(ge=1, le=200)] = 15
    rag_min_relevance_score: Probability = 0.48
    rag_max_context_characters: Annotated[int, Field(ge=500, le=100_000)] = 12_000

    # Conversation lifecycle
    conversation_store_backend: ConversationStoreBackend = ConversationStoreBackend.MEMORY
    session_idle_timeout_seconds: PositiveSeconds = 900
    session_max_duration_seconds: PositiveSeconds = 14_400
    transcript_context_turns: Annotated[int, Field(ge=1, le=100)] = 12
    live_workflow_timeout_seconds: PositiveSeconds = 25
    crm_workflow_timeout_seconds: PositiveSeconds = 45

    # Guardrails
    min_grounding_coverage: Probability = 1.0
    min_agent_confidence: Probability = 0.55
    require_human_review_on_violation: bool = True
    safe_fallback_response: str = (
        "I do not have enough approved product information to answer that reliably. "
        "Please verify with a product expert."
    )

    # API behavior
    api_prefix: str = "/api/v1"
    health_path: str = "/health"
    websocket_path: str = "/ws/copilot"
    enable_api_docs: bool = True
    max_document_upload_bytes: Annotated[int, Field(ge=1_024, le=104_857_600)] = 20_971_520

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        """Convert a comma-separated origin string to an immutable sequence."""

        if isinstance(value, str):
            origins = tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())
            if not origins:
                raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
            return origins
        return value

    @field_validator("supported_document_extensions", mode="before")
    @classmethod
    def parse_document_extensions(cls, value: object) -> object:
        """Normalize configured extensions to lowercase values with leading dots."""

        if isinstance(value, str):
            value = tuple(item.strip() for item in value.split(",") if item.strip())
        if isinstance(value, (tuple, list)):
            normalized = tuple(
                extension.lower() if extension.startswith(".") else f".{extension.lower()}"
                for extension in value
            )
            if not normalized:
                raise ValueError("SUPPORTED_DOCUMENT_EXTENSIONS cannot be empty")
            return normalized
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Validate and normalize Python logging level names."""

        normalized = value.strip().upper()
        supported = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in supported:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(supported)}")
        return normalized

    @field_validator(
        "app_name",
        "app_host",
        "app_version",
        "service_instance_id",
        "gemini_model",
        "whisper_model",
        "whisper_device",
        "whisper_compute_type",
        "embedding_model",
        "embedding_device",
        "chroma_collection",
        "safe_fallback_response",
    )
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        """Reject empty operational identifiers and model names."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be blank")
        return stripped

    @field_validator("api_prefix", "health_path", "websocket_path")
    @classmethod
    def normalize_route_path(cls, value: str) -> str:
        """Ensure route settings are absolute and have no trailing slash."""

        stripped = value.strip()
        if not stripped.startswith("/"):
            raise ValueError("route paths must start with '/'")
        return stripped.rstrip("/") or "/"

    @field_validator("whisper_language", mode="before")
    @classmethod
    def normalize_optional_language(cls, value: object) -> object:
        """Allow an empty language value to request Whisper auto-detection."""

        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized or None
        return value

    @field_validator("core_api_url", mode="before")
    @classmethod
    def normalize_optional_core_url(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().rstrip("/")
            return normalized or None
        return value

    @model_validator(mode="after")
    def validate_related_limits(self) -> Self:
        """Validate invariants involving multiple configuration fields."""

        if self.document_chunk_overlap >= self.document_chunk_size:
            raise ValueError("DOCUMENT_CHUNK_OVERLAP must be smaller than DOCUMENT_CHUNK_SIZE")
        if self.rag_fetch_k < self.rag_top_k:
            raise ValueError("RAG_FETCH_K must be greater than or equal to RAG_TOP_K")
        if self.transcription_window_seconds > self.max_audio_buffer_seconds:
            raise ValueError("TRANSCRIPTION_WINDOW_SECONDS cannot exceed MAX_AUDIO_BUFFER_SECONDS")
        if self.session_idle_timeout_seconds > self.session_max_duration_seconds:
            raise ValueError(
                "SESSION_IDLE_TIMEOUT_SECONDS cannot exceed SESSION_MAX_DURATION_SECONDS"
            )
        if self.app_env is AppEnvironment.PRODUCTION and self.app_debug:
            raise ValueError("APP_DEBUG must be false in production")
        if self.app_env is AppEnvironment.PRODUCTION and "*" in self.allowed_origins:
            raise ValueError("wildcard CORS origins are not allowed in production")
        if self.app_env is AppEnvironment.PRODUCTION and (
            not self.auth_required or self.jwt_secret is None or self.internal_api_key is None
        ):
            raise ValueError(
                "production requires AUTH_REQUIRED, JWT_SECRET, and INTERNAL_API_KEY"
            )
        return self

    @property
    def audio_bytes_per_second(self) -> int:
        """Return the expected byte rate for uncompressed PCM audio."""

        return self.audio_sample_rate_hz * self.audio_channels * self.audio_sample_width_bytes

    @property
    def audio_chunk_size_bytes(self) -> int:
        """Return the expected byte size of one configured PCM audio frame."""

        return self.audio_bytes_per_second * self.audio_chunk_duration_ms // 1_000

    @property
    def max_audio_buffer_bytes(self) -> int:
        """Return the hard per-session audio-buffer size in bytes."""

        return int(self.audio_bytes_per_second * self.max_audio_buffer_seconds)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache one immutable settings object for the process.

    Tests that modify environment variables should call ``get_settings.cache_clear``
    before requesting another instance.
    """

    return Settings()


__all__ = [
    "AppEnvironment",
    "ConversationStoreBackend",
    "LogFormat",
    "Settings",
    "get_settings",
]
