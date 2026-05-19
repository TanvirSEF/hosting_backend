# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    PROJECT_NAME: str = "NexHost Custom Automation API"
    DATABASE_URL: str
    JWT_SECRET: str
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    WHM_HOST: str = ""
    WHM_USERNAME: str = ""
    WHM_API_TOKEN: str = ""

settings = Settings()
