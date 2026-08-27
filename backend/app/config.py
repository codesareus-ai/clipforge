"""Central settings. All secrets come from env/.env — never hard-code credentials."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "ClipForge"
    ENV: str = "dev"

    # Storage (S3/R2) — needed for Instagram pull-from-URL
    S3_ENDPOINT: str | None = None
    S3_BUCKET: str | None = None
    S3_REGION: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    PUBLIC_BASE_URL: str = "https://cdn.example.com"  # base URL where clips are served

    # Transcription
    WHISPER_MODEL: str = "large-v3"
    WHISPER_DEVICE: str = "cuda"  # cuda | cpu
    USE_DIARIZATION: bool = False
    HF_TOKEN: str | None = None  # for WhisperX pyannote models

    # LLM ranking
    RANK_LLM_PROVIDER: str = "openai"  # openai | anthropic | gemini
    RANK_LLM_MODEL: str = "gpt-4o-mini"
    RANK_LLM_API_KEY: str | None = None

    # Render
    REMOTION_PROJECT_DIR: str = "../frontend"
    FFMPEG_BIN: str = "ffmpeg"
    OUTPUT_DIR: str = "./outputs"

    # Platform OAuth (client ids/secrets ONLY — never user tokens)
    TIKTOK_CLIENT_KEY: str | None = None
    TIKTOK_CLIENT_SECRET: str | None = None
    IG_APP_ID: str | None = None
    IG_APP_SECRET: str | None = None
    YT_CLIENT_ID: str | None = None
    YT_CLIENT_SECRET: str | None = None

    # Token vault encryption (Fernet key)
    TOKEN_ENCRYPTION_KEY: str | None = None

    # DB + worker
    DATABASE_URL: str = "sqlite:///./clipforge.db"
    REDIS_URL: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
