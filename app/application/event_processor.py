# app/application/event_processor.py
from typing import List
from app.application.interfaces import CampaignRepository, EventRepository, MessageRepository
from app.application.dtos import EventRequest, MessageResponse
from app.domain.models import UserEvent, CrmMessage
from app.domain.services import CampaignMatcher

class EventProcessor:
    """
    이벤트를 수신하여 적절한 마케팅 메시지를 생성하는 유즈케이스(Service)
    """

    # 의존성 주입 (Dependency Injection) - 인터페이스에 의존!
    def __init__(
        self,
        repository: CampaignRepository,
        event_repo: EventRepository,
        message_repo: MessageRepository
    ):
        self.repository = repository
        self.event_repo = event_repo
        self.message_repo = message_repo

    async def process_event(self, request: EventRequest) -> List[MessageResponse]:
        # 1. DTO -> Domain 모델 변환
        event = UserEvent(
            user_id=request.user_id,
            event_type=request.event_type,
            metadata=request.metadata
        )

        # 2. 이벤트 저장 (감사 로그)
        await self.event_repo.save(event)

        # 3. 활성 캠페인 목록 조회 (DB 접근)
        active_campaigns = await self.repository.get_active_campaigns()

        results = []
        messages_to_save = []

        # 4. 각 캠페인에 대해 조건 검사 (Domain Service 활용)
        for campaign in active_campaigns:
            if CampaignMatcher.is_match(campaign, event):
                # 5. 조건 만족 시 메시지 생성
                message = CrmMessage(
                    user_id=event.user_id,
                    campaign_id=campaign.id,
                    content=campaign.message_template
                )
                messages_to_save.append(message)

                results.append(MessageResponse(
                    user_id=message.user_id,
                    content=message.content,
                    campaign_name=campaign.name
                ))

        # 6. 생성된 메시지 저장
        if messages_to_save:
            await self.message_repo.save_all(messages_to_save)

        return results

    async def process_event_batch(self, requests: List[EventRequest]) -> List[MessageResponse]:
        """
        [성능 최적화] 대량의 이벤트를 한 번에 처리합니다.

        핵심 최적화:
        1. 캠페인을 한 번만 조회 (N번 → 1번 DB I/O)
        2. 메모리에서 모든 매칭 수행
        3. 네트워크 오버헤드 최소화

        Args:
            requests: 이벤트 요청 리스트

        Returns:
            모든 이벤트에 대한 메시지 응답 리스트
        """
        if not requests:
            return []

        # 1. 이벤트 리스트를 도메인 모델로 변환
        events = [
            UserEvent(
                user_id=r.user_id,
                event_type=r.event_type,
                metadata=r.metadata
            ) for r in requests
        ]

        # 2. 이벤트 배치 저장 (감사 로그)
        await self.event_repo.save_all(events)

        # 3. 활성 캠페인을 단 한 번만 조회 (핵심 최적화 포인트!)
        active_campaigns = await self.repository.get_active_campaigns()

        all_results = []
        messages_to_save = []

        # 4. 각 이벤트를 메모리에서 처리 (DB 접근 없음)
        for event in events:
            for campaign in active_campaigns:
                if CampaignMatcher.is_match(campaign, event):
                    message = CrmMessage(
                        user_id=event.user_id,
                        campaign_id=campaign.id,
                        content=campaign.message_template
                    )
                    messages_to_save.append(message)

                    all_results.append(MessageResponse(
                        user_id=message.user_id,
                        content=message.content,
                        campaign_name=campaign.name
                    ))

        # 5. 생성된 메시지 배치 저장
        if messages_to_save:
            await self.message_repo.save_all(messages_to_save)

        return all_results