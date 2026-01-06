# app/infrastructure/db/repositories.py
from typing import List
from app.application.interfaces import CampaignRepository
from app.domain.models import Campaign
from app.infrastructure.db.models import CampaignDocument

class MongoCampaignRepository(CampaignRepository):

    # 1. 도메인 객체 -> DB 문서로 변환 후 저장
    async def add(self, campaign: Campaign) -> Campaign:
        doc = CampaignDocument(
            name=campaign.name,
            target_event=campaign.target_event,
            min_cart_value=campaign.min_cart_value,
            message_template=campaign.message_template,
            status=campaign.status
        )
        await doc.insert() # MongoDB 저장
        # ID가 생성되었으므로 도메인 객체에 업데이트해서 반환
        campaign.id = str(doc.id)
        return campaign

    # 2. DB 문서 조회 -> 도메인 객체로 변환 후 반환
    async def get_active_campaigns(self) -> List[Campaign]:
        docs = await CampaignDocument.find(
            CampaignDocument.status == "active"
        ).to_list()

        # 변환 로직 (DB -> Domain)
        return [
            Campaign(
                id=str(doc.id),
                name=doc.name,
                target_event=doc.target_event,
                min_cart_value=doc.min_cart_value,
                message_template=doc.message_template,
                status=doc.status
            ) for doc in docs
        ]