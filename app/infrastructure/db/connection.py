# app/infrastructure/db/connection.py
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.infrastructure.db.models import CampaignDocument

async def connect_to_mongo():
    # 1. 비동기 클라이언트 생성
    client = AsyncIOMotorClient(settings.DATABASE_URL)

    # 2. DB 선택
    database = client[settings.DATABASE_NAME]

    # 3. Beanie 초기화 (Document 모델 등록)
    # 여기에 모델을 등록해야 DB와 매핑이 됩니다.
    await init_beanie(database=database, document_models=[CampaignDocument])

    print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")