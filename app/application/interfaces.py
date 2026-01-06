# app/application/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import Campaign

class CampaignRepository(ABC):
    @abstractmethod
    async def add(self, campaign: Campaign) -> Campaign:
        pass

    @abstractmethod
    async def get_active_campaigns(self) -> List[Campaign]:
        pass