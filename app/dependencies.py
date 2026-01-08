# app/dependencies.py
from app.infrastructure.db.repositories import MongoCampaignRepository
from app.application.event_processor import EventProcessor

# Spring의 @Bean 정의와 비슷합니다.
def get_campaign_repository() -> MongoCampaignRepository:
    return MongoCampaignRepository()

# Service에 Repository를 주입(Autowired)하는 과정
# FastAPI의 Depends가 이 함수를 호출해서 의존성을 해결합니다.
def get_event_processor() -> EventProcessor:
    repository = get_campaign_repository()
    return EventProcessor(repository)