# app/application/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from app.domain.models import Campaign, UserEvent, CrmMessage, CampaignStatus

class CampaignRepository(ABC):
    @abstractmethod
    async def add(self, campaign: Campaign) -> Campaign:
        pass

    @abstractmethod
    async def get_active_campaigns(self) -> List[Campaign]:
        pass

    @abstractmethod
    async def add_all(self, campaigns: List[Campaign]) -> bool:
        pass

    @abstractmethod
    async def get_campaigns(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        status: Optional[CampaignStatus] = None
    ) -> Tuple[List[Campaign], Optional[str]]:
        """
        커서 기반 페이지네이션으로 캠페인 목록을 조회합니다.

        Args:
            cursor: 마지막으로 본 항목의 ID (첫 페이지 시 None)
            limit: 페이지당 항목 수 (1~100)
            status: 상태별 필터 (None이면 전체)

        Returns:
            (campaigns, next_cursor)
            - next_cursor: 다음 페이지가 있으면 마지막 항목의 ID, 없으면 None
        """
        pass


class EventRepository(ABC):
    @abstractmethod
    async def save(self, event: UserEvent) -> UserEvent:
        pass

    @abstractmethod
    async def save_all(self, events: List[UserEvent]) -> bool:
        pass


class MessageRepository(ABC):
    @abstractmethod
    async def save(self, message: CrmMessage) -> CrmMessage:
        pass

    @abstractmethod
    async def save_all(self, messages: List[CrmMessage]) -> bool:
        pass


class CacheService(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass