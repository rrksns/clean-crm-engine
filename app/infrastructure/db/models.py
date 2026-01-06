# app/infrastructure/db/models.py
from beanie import Document
from datetime import datetime
from typing import Optional
from app.domain.models import EventType, CampaignStatus

# MongoDB 컬렉션에 저장될 실제 형태
class CampaignDocument(Document):
    # ID는 MongoDB가 자동 생성 (_id)
    name: str
    target_event: EventType
    min_cart_value: Optional[int]
    message_template: str
    status: CampaignStatus
    created_at: datetime = datetime.now()

    class Settings:
        name = "campaigns"  # MongoDB Collection 이름 (테이블명)