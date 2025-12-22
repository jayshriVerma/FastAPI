from typing import Dict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str
    VALID_API_KEYS: Dict[str, str]

    class Config:
        env_file = ".env"

settings = Settings()
