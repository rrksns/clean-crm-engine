from app.domain.models import Campaign, UserEvent, CampaignStatus

class CampaignMatcher:
    """
    이벤트가 발생했을 때, 해당 이벤트가 캠페인 조건에 부합하는지 판단하는 도메인 서비스
    """

    @staticmethod
    def is_match(campaign: Campaign, event: UserEvent) -> bool:
        # 1. 캠페인이 활성 상태가 아니면 매칭 실패
        if campaign.status != CampaignStatus.ACTIVE:
            return False

        # 2. 이벤트 타입이 다르면 매칭 실패
        if campaign.target_event != event.event_type:
            return False

        # 3. (비즈니스 로직) 장바구니 금액 조건 체크
        # 이벤트 메타데이터에 'price'가 있다고 가정
        if campaign.min_cart_value > 0:
            event_price = event.metadata.get("price", 0)
            if event_price < campaign.min_cart_value:
                return False

        return True