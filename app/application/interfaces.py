# app/application/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import Campaign, UserEvent, CrmMessage

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