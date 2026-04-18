"""Application settings loaded from environment variables / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    GEMINI_API_KEY: str
    CLASSIFIER_MODEL: str = "gemini-2.5-flash"
    MAIN_AGENT_MODEL: str = "gemini-2.5-flash"
    MAX_RUN_AGE_HOURS: int = 72
    SCHEDULER_INTERVAL_SECONDS: int = 60


settings = Settings()
