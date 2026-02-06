# app/core/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 환경 식별 (dev / staging / prod)
    ENVIRONMENT: str = "dev"

    # MongoDB 연결
    DATABASE_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "clean_crm_db"

    # Redis 연결
    REDIS_URL: str = "redis://localhost:6379/0"

    # 로깅
    LOG_LEVEL: str = "INFO"

    # API
    API_VERSION: str = "v1"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "prod"

    @property
    def is_debug(self) -> bool:
        return self.ENVIRONMENT == "dev"

    class Config:
        # ENVIRONMENT 환경변수로 env_file을 동적 선택
        env_file = os.getenv("ENV_FILE", ".env.dev")

settings = Settings()