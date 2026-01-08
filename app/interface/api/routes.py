# app/interface/api/routes.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.application.dtos import EventRequest, MessageResponse, CampaignCreateRequest
from app.application.event_processor import EventProcessor
from app.dependencies import get_event_processor, get_campaign_repository
from app.application.interfaces import CampaignRepository
from app.domain.models import Campaign, CampaignStatus

router = APIRouter()

# --- 1. 이벤트 수신 API (메인 기능) ---
@router.post("/events", response_model=List[MessageResponse])
async def track_event(
        request: EventRequest,
        # @Autowired: 의존성 주입이 여기서 일어납니다!
        processor: EventProcessor = Depends(get_event_processor)
):
    """
    사용자 행동 이벤트를 수신하고, 조건에 맞는 캠페인 메시지를 반환합니다.
    """
    results = await processor.process_event(request)
    return results

# --- 2. 캠페인 등록 API (데이터 세팅용) ---
@router.post("/campaigns", status_code=201)
async def create_campaign(
        request: CampaignCreateRequest,
        repo: CampaignRepository = Depends(get_campaign_repository)
):
    """
    마케터가 새로운 캠페인 규칙을 등록합니다.
    """
    # DTO -> Domain 변환 (간단해서 여기서 처리하지만, 복잡하면 Service로 위임)
    new_campaign = Campaign(
        id="", # DB 저장 시 생성됨
        name=request.name,
        target_event=request.target_event,
        min_cart_value=request.min_cart_value,
        message_template=request.message_template,
        status=CampaignStatus.ACTIVE
    )

    saved_campaign = await repo.add(new_campaign)
    return {"id": saved_campaign.id, "message": "Campaign created successfully"}