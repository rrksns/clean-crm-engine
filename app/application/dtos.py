# app/application/dtos.py
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.domain.models import EventType

# 1. 프론트엔드에서 보낼 이벤트 요청 (Request DTO)
class EventRequest(BaseModel):
    user_id: str
    event_type: EventType
    metadata: Dict[str, Any] = {}

# 2. 마케터가 캠페인을 등록할 때 쓸 요청 (Request DTO)
class CampaignCreateRequest(BaseModel):
    name: str
    target_event: EventType
    min_cart_value: Optional[int] = 0
    message_template: str

# 3. 결과로 돌려줄 메시지 응답 (Response DTO)
class MessageResponse(BaseModel):
    user_id: str
    content: str
    campaign_name: str