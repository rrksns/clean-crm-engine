# app/infrastructure/db/connection.py
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from typing import Optional
from app.core.config import settings
from app.infrastructure.db.models import CampaignDocument

# 전역 변수: DB 클라이언트 (헬스체크 등에서 사용)
_client: Optional[AsyncIOMotorClient] = None
_database = None


async def connect_to_mongo():
    """
    MongoDB에 연결하고 Beanie를 초기화합니다.

    이 함수는 애플리케이션 시작 시 한 번만 호출됩니다.
    """
    global _client, _database

    # 1. 비동기 클라이언트 생성
    _client = AsyncIOMotorClient(settings.DATABASE_URL)

    # 2. DB 선택
    _database = _client[settings.DATABASE_NAME]

    # 3. Beanie 초기화 (Document 모델 등록)
    # 여기에 모델을 등록해야 DB와 매핑이 됩니다.
    await init_beanie(database=_database, document_models=[CampaignDocument])

    print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")


def get_db_client() -> Optional[AsyncIOMotorClient]:
    """
    DB 클라이언트 인스턴스를 반환합니다.

    Returns:
        AsyncIOMotorClient 또는 None (연결 전)
    """
    return _client


def get_database():
    """
    데이터베이스 인스턴스를 반환합니다.

    Returns:
        Database 또는 None (연결 전)
    """
    return _database