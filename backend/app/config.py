import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

LOCAL_SETTINGS_PATH = Path(__file__).resolve().parents[1] / 'local-settings.json'


def local_settings():
    """Private checkout configuration, independent of the working directory."""
    if not LOCAL_SETTINGS_PATH.exists():
        return {}
    try:
        config = json.loads(LOCAL_SETTINGS_PATH.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise ValueError('Unable to read backend/local-settings.json. Check its JSON syntax.') from exc
    result = {key: config[key] for key in ('app_origin', 'cookie_secure') if key in config}
    database = config.get('database', {})
    if database.get('password'):
        result['database_url'] = URL.create(
            'postgresql+psycopg',
            username=database.get('username', 'postgres'),
            password=database['password'],
            host=database.get('host', 'localhost'),
            port=database.get('port', 5432),
            database=database.get('name', 'college_twin'),
        ).render_as_string(hide_password=False)
    return result


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    database_url: str
    app_origin: str = "http://localhost:8080"
    cookie_secure: bool = False
    session_hours: int = Field(default=8, ge=1, le=24)

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return init_settings, env_settings, dotenv_settings, local_settings, file_secret_settings


@lru_cache
def settings() -> Settings:
    return Settings()
