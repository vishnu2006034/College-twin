from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    app_origin: str = "http://localhost:8080"
    cookie_secure: bool = False
    session_hours: int = Field(default=8, ge=1, le=24)


@lru_cache
def settings() -> Settings:
    return Settings()
