from typing import List, Union
import json
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General
    PROJECT_NAME: str = "Study Assistant AI Chatbot"
    ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/chatbot_db",
        description="Async database connection string"
    )
    SQL_ECHO: bool = False

    # Redis Cache & Sessions
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # LLM Settings
    DEFAULT_LLM_PROVIDER: str = "claude"
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic Claude API Key"
    )
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_TIMEOUT_SECONDS: float = 60.0

    # Rate Limiting & Memory
    RATE_LIMIT_PER_MINUTE: int = 20
    MAX_HISTORY_MESSAGES: int = 10


settings = Settings()
