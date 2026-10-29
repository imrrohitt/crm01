"""
Application settings loaded from environment.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration from environment. Loaded via get_settings()."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "MyApp"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/myapp"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # JWT
    JWT_SECRET_KEY: str = "jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Public URLs
    FRONTEND_URL: str = "http://localhost:3000"

    # Instagram (Instagram API with Instagram Login). Use the *Instagram* app id/secret
    # from the Meta app's Instagram product page, not Settings -> Basic.
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    # Must match "Valid OAuth redirect URIs" in the Meta app exactly. The API must be
    # reachable at this URL (ngrok https URL in development).
    INSTAGRAM_REDIRECT_URI: str = ""
    INSTAGRAM_API_VERSION: str = "v24.0"
    INSTAGRAM_SCOPES: str = "instagram_business_basic,instagram_business_manage_messages,instagram_business_manage_comments"

    # Secret used to encrypt stored access tokens (any long random string; see README).
    ENCRYPTION_KEY: str = ""

    # CORS (browser origins allowed to call the API)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Subscriptions: while False every active tenant is treated as subscribed.
    SUBSCRIPTION_ENFORCED: bool = False

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# Celery configuration (task queues, serialization, timezone)
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True

# Named queues 
CELERY_TASK_QUEUES = ["default", "mailers", "critical", "low_priority"]
CELERY_DEFAULT_QUEUE = "default"

# Celery Beat schedule (periodic tasks) — add your scheduled jobs here
CELERY_BEAT_SCHEDULE: dict = {}
