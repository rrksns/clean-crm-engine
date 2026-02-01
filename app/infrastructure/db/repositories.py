# app/infrastructure/db/repositories.py
from typing import List
from pymongo.errors import PyMongoError, DuplicateKeyError
from app.application.interfaces import CampaignRepository
from app.domain.models import Campaign
from app.infrastructure.db.models import CampaignDocument
from app.core.exceptions import (
    DatabaseQueryException,
    DuplicateResourceException
)

class MongoCampaignRepository(CampaignRepository):

    # 1. 도메인 객체 -> DB 문서로 변환 후 저장
    async def add(self, campaign: Campaign) -> Campaign:
        try:
            doc = CampaignDocument(
                name=campaign.name,
                target_event=campaign.target_event,
                min_cart_value=campaign.min_cart_value,
                message_template=campaign.message_template,
                status=campaign.status
            )
            await doc.insert()  # MongoDB 저장
            # ID가 생성되었으므로 도메인 객체에 업데이트해서 반환
            campaign.id = str(doc.id)
            return campaign

        except DuplicateKeyError as e:
            # 중복 키 에러 (예: 캠페인 이름이 unique index인 경우)
            raise DuplicateResourceException(
                resource_type="Campaign",
                field="name",
                value=campaign.name
            ) from e

        except PyMongoError as e:
            # 기타 MongoDB 에러
            raise DatabaseQueryException(
                operation="insert",
                details=str(e)
            ) from e

    # 2. DB 문서 조회 -> 도메인 객체로 변환 후 반환
    async def get_active_campaigns(self) -> List[Campaign]:
        try:
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

        except PyMongoError as e:
            # MongoDB 쿼리 실행 실패
            raise DatabaseQueryException(
                operation="find active campaigns",
                details=str(e)
            ) from e

    # 3. 배치 삽입 (성능 최적화)
    async def add_all(self, campaigns: List[Campaign]) -> bool:
        """
        여러 캠페인을 한 번에 저장합니다 (Batch Insert)

        Args:
            campaigns: 저장할 캠페인 리스트

        Returns:
            성공 여부

        Raises:
            DatabaseQueryException: DB 작업 실패 시
        """
        if not campaigns:
            return False

        try:
            # 도메인 객체 -> DB 문서(Document) 리스트로 변환
            docs = [
                CampaignDocument(
                    name=c.name,
                    target_event=c.target_event,
                    min_cart_value=c.min_cart_value,
                    message_template=c.message_template,
                    status=c.status
                ) for c in campaigns
            ]

            # ✨ 핵심: 한 번의 쿼리로 모두 저장 (Batch Insert)
            await CampaignDocument.insert_many(docs)
            return True

        except PyMongoError as e:
            # MongoDB 배치 삽입 실패
            raise DatabaseQueryException(
                operation="batch insert campaigns",
                details=str(e)
            ) from e