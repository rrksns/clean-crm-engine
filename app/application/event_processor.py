# app/application/event_processor.py
from typing import List
from app.application.interfaces import CampaignRepository
from app.application.dtos import EventRequest, MessageResponse
from app.domain.models import UserEvent, CrmMessage
from app.domain.services import CampaignMatcher

class EventProcessor:
    """
    이벤트를 수신하여 적절한 마케팅 메시지를 생성하는 유즈케이스(Service)
    """

    # 의존성 주입 (Dependency Injection) - 인터페이스에 의존!
    def __init__(self, repository: CampaignRepository):
        self.repository = repository

    async def process_event(self, request: EventRequest) -> List[MessageResponse]:
        # 1. DTO -> Domain 모델 변환
        event = UserEvent(
            user_id=request.user_id,
            event_type=request.event_type,
            metadata=request.metadata
        )

        # 2. 활성 캠페인 목록 조회 (DB 접근)
        active_campaigns = await self.repository.get_active_campaigns()

        results = []

        # 3. 각 캠페인에 대해 조건 검사 (Domain Service 활용)
        for campaign in active_campaigns:
            if CampaignMatcher.is_match(campaign, event):
                # 4. 조건 만족 시 메시지 생성
                message = CrmMessage(
                    user_id=event.user_id,
                    campaign_id=campaign.id,
                    content=campaign.message_template
                )

                # 5. Response DTO로 변환하여 결과 목록에 추가
                results.append(MessageResponse(
                    user_id=message.user_id,
                    content=message.content,
                    campaign_name=campaign.name
                ))

        return results