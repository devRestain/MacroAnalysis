from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://macro:macro@postgres:5432/macrodb"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # API Keys
    FRED_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    EXCHANGERATE_API_KEY: str = ""
    NEWS_API_KEY: str = ""

    # App
    APP_ENV: str = "production"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]

    # AI
    AI_MODEL: str = "gpt-4o-mini"
    AI_SUMMARY_HOUR_KST: int = 6  # 06:30 KST

    # Sentiment Pipeline (v2)
    SENTIMENT_BATCH_SIZE: int = 20
    INERTIA_ALPHA: float = 0.05
    DIVERGENCE_WARNING_THRESHOLD: float = 0.25
    DIVERGENCE_ALERT_THRESHOLD: float = 0.40

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
