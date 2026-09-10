from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Default to a local SQLite file for local tests/demos. Override via .env in real deployments.
    database_url: str = "sqlite:///./fraumatch_demo.db"
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    openai_api_key: Optional[str] = None


settings = Settings()
