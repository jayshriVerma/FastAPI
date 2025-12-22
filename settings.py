from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: str
    VALID_API_KEYS: Dict[str, str]

    model_config = SettingsConfigDict(
        env_file = ".env",
        )

settings = Settings()
