from app.domain.models import Campaign, UserEvent, EventType, CampaignStatus
from app.domain.services import CampaignMatcher

def test_campaign_matching_logic():
    # Given: 5만원 이상 구매 시 발동하는 캠페인
    campaign = Campaign(
        id="camp_001",
        name="High Value Cart",
        target_event=EventType.ADD_TO_CART,
        min_cart_value=50000,
        message_template="무료배송 쿠폰!"
    )

    # When 1: 3만원짜리 물건을 담음 -> 매칭 실패해야 함
    event_low = UserEvent(
        user_id="user_1",
        event_type=EventType.ADD_TO_CART,
        metadata={"price": 30000}
    )

    # When 2: 6만원짜리 물건을 담음 -> 매칭 성공해야 함
    event_high = UserEvent(
        user_id="user_1",
        event_type=EventType.ADD_TO_CART,
        metadata={"price": 60000}
    )

    # Then
    assert CampaignMatcher.is_match(campaign, event_low) == False
    assert CampaignMatcher.is_match(campaign, event_high) == True
    print("✅ 도메인 로직 테스트 통과!")

if __name__ == "__main__":
    test_campaign_matching_logic()