from pydantic_settings import BaseSettings
from functools import cached_property
from pathlib import Path


class Settings(BaseSettings):
    SECRET_KEY: str
    DB_URL: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    DEFAULT_DEV_TENANT: str = "public"
    PROD_ENV: str = "prod"

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / ".env")
        extra = "ignore"

    @cached_property
    def ASYNC_DB_URL(self) -> str:
        return self.DB_URL

    @cached_property
    def SYNC_DB_URL(self) -> str:
        return self.DB_URL.replace("asyncpg", "psycopg")
    

settings = Settings() 