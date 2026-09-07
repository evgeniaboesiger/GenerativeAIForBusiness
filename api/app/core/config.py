from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Default to a local SQLite file for local tests/demos. Override via .env in real deployments.
    database_url: str = "sqlite:///./fraumatch_demo.db"
    supabase_url: str | None = None
    supabase_key: str | None = None
    openai_api_key: str | None = None


settings = Settings()
