import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000

    # DB and Redis settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/sales_copilot"
    DATABASE_SQLITE_URL: str = "sqlite:///./sales_copilot.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    INTERNAL_API_KEY: Optional[str] = None
    AUTH_REQUIRED: bool = False
    JWT_SECRET: Optional[str] = None
    JWT_ACCESS_MINUTES: int = 60
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 240

    # Encryption key for PII (Must be a base64 encoded Fernet key)
    # Default fallback for testing only
    ENCRYPTION_KEY: str = "3J3V5eT3k7z2b8d9V6c7X8z9y0A1B2C3D4E5F6G7H8I="

    # API Keys
    GEMINI_API_KEY: Optional[str] = None
    DEEPGRAM_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"
    ELEVENLABS_MODEL_ID: str = "eleven_flash_v2_5"

    # Model parameters
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    # Use SQLite for testing or if PG is not configured
    USE_SQLITE: bool = True

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
