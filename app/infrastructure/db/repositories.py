# app/infrastructure/db/repositories.py
import json
import logging
from typing import List, Optional, Tuple
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
from bson.errors import InvalidId
from app.application.interfaces import CampaignRepository, EventRepository, MessageRepository, CacheService
from app.domain.models import Campaign, UserEvent, CrmMessage, CampaignStatus
from app.infrastructure.db.models import CampaignDocument, UserEventDocument, CrmMessageDocument
from app.core.exceptions import (
    DatabaseQueryException,
    DuplicateResourceException,
    ValidationException
)

# 로깅 설정
logger = logging.getLogger(__name__)

# 캐시 키 및 TTL 상수
ACTIVE_CAMPAIGNS_CACHE_KEY = "crm:campaigns:active"
ACTIVE_CAMPAIGNS_TTL = 300  # 5분

class MongoCampaignRepository(CampaignRepository):

    def __init__(self, cache: Optional[CacheService] = None):
        """
        캠페인 Repository 생성자.

        Args:
            cache: 캐시 서비스 (None이면 캐시 없이 동작)
        """
        self.cache = cache

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

            # ✨ 캐시 무효화 (새 캠페인이 추가되었으므로)
            await self._invalidate_cache()

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
        """
        활성 캠페인 목록을 조회합니다 (Cache-Aside 패턴).

        흐름:
        1. 캐시 확인 → 히트하면 즉시 반환
        2. 캐시 미스 → DB 조회
        3. DB 결과를 캐시에 저장 (TTL 5분)
        4. 결과 반환
        """
        # ✨ Step 1: 캐시 조회
        cached_campaigns = await self._get_from_cache()
        if cached_campaigns is not None:
            logger.info(f"캐시에서 활성 캠페인 조회 성공 ({len(cached_campaigns)}개)")
            return cached_campaigns

        # ✨ Step 2: 캐시 미스 → DB 조회
        try:
            docs = await CampaignDocument.find(
                CampaignDocument.status == "active"
            ).to_list()

            # 변환 로직 (DB -> Domain)
            campaigns = [
                Campaign(
                    id=str(doc.id),
                    name=doc.name,
                    target_event=doc.target_event,
                    min_cart_value=doc.min_cart_value,
                    message_template=doc.message_template,
                    status=doc.status
                ) for doc in docs
            ]

            # ✨ Step 3: DB 결과를 캐시에 저장
            await self._set_to_cache(campaigns)
            logger.info(f"DB에서 활성 캠페인 조회 및 캐시 저장 ({len(campaigns)}개)")

            return campaigns

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

            # ✨ 캐시 무효화 (새 캠페인들이 추가되었으므로)
            await self._invalidate_cache()

            return True

        except PyMongoError as e:
            # MongoDB 배치 삽입 실패
            raise DatabaseQueryException(
                operation="batch insert campaigns",
                details=str(e)
            ) from e


    # 4. 커서 기반 페이지네이션 조회
    async def get_campaigns(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        status: Optional[CampaignStatus] = None
    ) -> Tuple[List[Campaign], Optional[str]]:
        try:
            # 필터 구성
            filter_query = {}
            if status:
                filter_query["status"] = status.value
            if cursor:
                try:
                    filter_query["_id"] = {"$lt": ObjectId(cursor)}
                except InvalidId:
                    raise ValidationException(
                        field="cursor",
                        reason="유효하지 않은 커서 형식입니다"
                    )

            # limit + 1개 조회 → 다음 페이지 존재 여부 판단
            docs = await CampaignDocument.find(filter_query) \
                .sort([("_id", -1)]) \
                .limit(limit + 1) \
                .to_list()

            has_next = len(docs) > limit
            if has_next:
                docs = docs[:limit]  # 초과분 제거

            campaigns = [
                Campaign(
                    id=str(doc.id),
                    name=doc.name,
                    target_event=doc.target_event,
                    min_cart_value=doc.min_cart_value,
                    message_template=doc.message_template,
                    status=doc.status
                ) for doc in docs
            ]

            next_cursor = str(docs[-1].id) if has_next else None

            return campaigns, next_cursor

        except ValidationException:
            raise  # ValidationException는 그대로 전파
        except PyMongoError as e:
            raise DatabaseQueryException(
                operation="get campaigns paginated",
                details=str(e)
            ) from e

    # ──────────────────────────────────────────────────
    # 캐시 헬퍼 메서드 (Private)
    # ──────────────────────────────────────────────────

    async def _get_from_cache(self) -> Optional[List[Campaign]]:
        """
        캐시에서 활성 캠페인 목록을 조회합니다.

        Returns:
            캐시된 캠페인 리스트 또는 None (캐시 미스)
        """
        if self.cache is None:
            return None

        try:
            cached_value = await self.cache.get(ACTIVE_CAMPAIGNS_CACHE_KEY)
            if cached_value is None:
                return None

            # JSON 문자열 -> 딕셔너리 리스트 -> Campaign 객체 리스트
            data = json.loads(cached_value)
            campaigns = [Campaign(**item) for item in data]
            return campaigns

        except Exception as e:
            logger.warning(f"캐시 역직렬화 실패: {e}")
            return None

    async def _set_to_cache(self, campaigns: List[Campaign]) -> None:
        """
        활성 캠페인 목록을 캐시에 저장합니다.

        Args:
            campaigns: 캐시에 저장할 캠페인 리스트
        """
        if self.cache is None:
            return

        try:
            # Campaign 객체 리스트 -> 딕셔너리 리스트 -> JSON 문자열
            data = [c.model_dump() for c in campaigns]
            json_value = json.dumps(data)
            await self.cache.set(
                ACTIVE_CAMPAIGNS_CACHE_KEY,
                json_value,
                ACTIVE_CAMPAIGNS_TTL
            )
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {e}")

    async def _invalidate_cache(self) -> None:
        """
        활성 캠페인 캐시를 무효화합니다.
        캠페인 추가/수정 시 호출됩니다.
        """
        if self.cache is None:
            return

        try:
            await self.cache.delete(ACTIVE_CAMPAIGNS_CACHE_KEY)
            logger.debug("활성 캠페인 캐시 무효화 완료")
        except Exception as e:
            logger.warning(f"캐시 무효화 실패: {e}")


class MongoEventRepository(EventRepository):

    async def save(self, event: UserEvent) -> UserEvent:
        try:
            doc = UserEventDocument(
                user_id=event.user_id,
                event_type=event.event_type,
                metadata=event.metadata,
                occurred_at=event.occurred_at
            )
            await doc.insert()
            return event

        except PyMongoError as e:
            raise DatabaseQueryException(
                operation="insert user event",
                details=str(e)
            ) from e

    async def save_all(self, events: List[UserEvent]) -> bool:
        if not events:
            return False

        try:
            docs = [
                UserEventDocument(
                    user_id=e.user_id,
                    event_type=e.event_type,
                    metadata=e.metadata,
                    occurred_at=e.occurred_at
                ) for e in events
            ]
            await UserEventDocument.insert_many(docs)
            return True

        except PyMongoError as e:
            raise DatabaseQueryException(
                operation="batch insert user events",
                details=str(e)
            ) from e


class MongoMessageRepository(MessageRepository):

    async def save(self, message: CrmMessage) -> CrmMessage:
        try:
            doc = CrmMessageDocument(
                user_id=message.user_id,
                campaign_id=message.campaign_id,
                campaign_name="",
                content=message.content,
                sent_at=message.sent_at
            )
            await doc.insert()
            return message

        except PyMongoError as e:
            raise DatabaseQueryException(
                operation="insert crm message",
                details=str(e)
            ) from e

    async def save_all(self, messages: List[CrmMessage]) -> bool:
        if not messages:
            return False

        try:
            docs = [
                CrmMessageDocument(
                    user_id=m.user_id,
                    campaign_id=m.campaign_id,
                    campaign_name="",
                    content=m.content,
                    sent_at=m.sent_at
                ) for m in messages
            ]
            await CrmMessageDocument.insert_many(docs)
            return True

        except PyMongoError as e:
            raise DatabaseQueryException(
                operation="batch insert crm messages",
                details=str(e)
            ) from e