# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    PROJECT_NAME: str = "NexHost Custom Automation API"
    DATABASE_URL: str
    JWT_SECRET: str
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CORS_ORIGINS: str = "http://127.0.0.1:3000,http://localhost:3000"
    RATE_LIMIT_PER_MINUTE: int = 120
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PROVIDER_CREDENTIAL_ENCRYPTION_KEY: str = ""
    WHM_HOST: str = ""
    WHM_USERNAME: str = ""
    WHM_API_TOKEN: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
