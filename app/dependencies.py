# app/dependencies.py
from app.infrastructure.db.repositories import (
    MongoCampaignRepository,
    MongoEventRepository,
    MongoMessageRepository
)
from app.infrastructure.cache.redis_cache import RedisCacheService
from app.application.event_processor import EventProcessor

# Spring의 @Bean 정의와 비슷합니다.
def get_campaign_repository() -> MongoCampaignRepository:
    return MongoCampaignRepository(cache=RedisCacheService())

def get_event_repository() -> MongoEventRepository:
    return MongoEventRepository()

def get_message_repository() -> MongoMessageRepository:
    return MongoMessageRepository()

# Service에 Repository를 주입(Autowired)하는 과정
# FastAPI의 Depends가 이 함수를 호출해서 의존성을 해결합니다.
def get_event_processor() -> EventProcessor:
    return EventProcessor(
        repository=get_campaign_repository(),
        event_repo=get_event_repository(),
        message_repo=get_message_repository()
    )