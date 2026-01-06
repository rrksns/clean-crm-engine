# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 기본값은 로컬 MongoDB 주소
    DATABASE_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "clean_crm_db"

    class Config:
        env_file = ".env"

settings = Settings()