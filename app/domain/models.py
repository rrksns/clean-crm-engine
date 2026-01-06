from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# --- Enums (상수 정의) ---
class EventType(str, Enum):
    LOGIN = "login"
    VIEW_PRODUCT = "view_product"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"

class CampaignStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"

# --- Domain Entities (순수 객체) ---

# 1. 사용자 행동 이벤트 (User Event)
class UserEvent(BaseModel):
    user_id: str
    event_type: EventType
    occurred_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = {}  # 예: {"product_id": "123", "price": 50000}

# 2. 캠페인 (Campaign) - 마케팅 규칙
class Campaign(BaseModel):
    id: str
    name: str
    target_event: EventType  # 어떤 행동을 했을 때 발동? (예: 장바구니 담기)
    min_cart_value: Optional[int] = 0  # 조건: 최소 금액 (예: 5만원 이상)
    message_template: str  # 보낼 메시지 (예: "배송비 무료 쿠폰 도착!")
    status: CampaignStatus = CampaignStatus.ACTIVE

# 3. CRM 메시지 (Message) - 결과물
class CrmMessage(BaseModel):
    user_id: str
    campaign_id: str
    content: str
    sent_at: datetime = Field(default_factory=datetime.now)