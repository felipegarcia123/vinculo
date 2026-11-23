from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")
    database_url: str = "sqlite:///./vinculo_local.db"
    auth_cookie_secure: bool = False
    auth_rate_limit_secret: str = ""
    vinculo_demo_only: bool = True
    cors_origins: str = "http://localhost:3000"
    loyalty_inactive_days: int = 30
    loyalty_llm_enabled: bool = False
    loyalty_llm_api_key: str | None = None
    loyalty_llm_base_url: str = "https://api.openai.com/v1"
    loyalty_llm_model: str = "gpt-4.1-mini"
    loyalty_llm_timeout_seconds: float = 12


settings = Settings()
