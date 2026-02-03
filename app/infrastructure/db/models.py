# app/infrastructure/db/models.py
from beanie import Document
from datetime import datetime
from typing import Optional, Dict, Any
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


class UserEventDocument(Document):
    """사용자 행동 이벤트 저장 (감사 로그)"""
    user_id: str
    event_type: EventType
    metadata: Dict[str, Any] = {}
    occurred_at: datetime = datetime.now()

    class Settings:
        name = "user_events"


class CrmMessageDocument(Document):
    """캠페인 조건 충족 시 생성된 메시지 저장"""
    user_id: str
    campaign_id: str
    campaign_name: str
    content: str
    sent_at: datetime = datetime.now()

    class Settings:
        name = "crm_messages"