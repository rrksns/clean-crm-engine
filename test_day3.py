# test_day3.py
import asyncio
from typing import List
from app.application.interfaces import CampaignRepository
from app.domain.models import Campaign, EventType, CampaignStatus
from app.application.event_processor import EventProcessor
from app.application.dtos import EventRequest

# 1. 가짜 저장소 만들기 (In-Memory DB)
# 실제 DB 연결 없이 List로 동작하는 Mock 클래스입니다.
class FakeCampaignRepository(CampaignRepository):
    def __init__(self):
        self.store = [] # DB 대신 리스트 사용

    async def add(self, campaign: Campaign) -> Campaign:
        self.store.append(campaign)
        return campaign

    async def get_active_campaigns(self) -> List[Campaign]:
        return [c for c in self.store if c.status == CampaignStatus.ACTIVE]

# 2. 테스트 시나리오 실행
async def test_logic():
    # 준비 (Given)
    fake_repo = FakeCampaignRepository()
    processor = EventProcessor(repository=fake_repo) # 가짜 DB 주입!

    # 캠페인 데이터 미리 세팅 (장바구니 5만원 이상 시 쿠폰 발급)
    await fake_repo.add(Campaign(
        id="camp_1",
        name="VIP Promotion",
        target_event=EventType.ADD_TO_CART,
        min_cart_value=50000,
        message_template="🎁 5천원 할인 쿠폰이 도착했습니다!",
        status=CampaignStatus.ACTIVE
    ))

    print("🧪 테스트 시작: 장바구니 이벤트 처리 로직 검증")

    # 상황 1: 3만원 담음 -> 쿠폰 안 나와야 함
    req_fail = EventRequest(
        user_id="user_1",
        event_type=EventType.ADD_TO_CART,
        metadata={"price": 30000}
    )
    result_fail = await processor.process_event(req_fail)
    assert len(result_fail) == 0
    print("✅ 상황 1 통과: 조건 미달 시 메시지 없음")

    # 상황 2: 7만원 담음 -> 쿠폰 나와야 함
    req_success = EventRequest(
        user_id="user_2",
        event_type=EventType.ADD_TO_CART,
        metadata={"price": 70000}
    )
    result_success = await processor.process_event(req_success)

    assert len(result_success) == 1
    assert result_success[0].content == "🎁 5천원 할인 쿠폰이 도착했습니다!"
    print(f"✅ 상황 2 통과: 메시지 발송됨 -> '{result_success[0].content}'")

if __name__ == "__main__":
    asyncio.run(test_logic())