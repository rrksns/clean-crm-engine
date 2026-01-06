# test_day2.py
import asyncio
from app.infrastructure.db.connection import connect_to_mongo
from app.infrastructure.db.repositories import MongoCampaignRepository
from app.domain.models import Campaign, EventType

async def main():
    # 1. DB 연결
    await connect_to_mongo()

    # 2. Repository 생성
    repo = MongoCampaignRepository()

    # 3. 도메인 객체 생성 (ID 없음)
    new_campaign = Campaign(
        id="", # DB 저장 전엔 ID 없음
        name="Day2 Test Campaign",
        target_event=EventType.LOGIN,
        min_cart_value=0,
        message_template="환영합니다!"
    )

    # 4. 저장 (Save)
    saved_campaign = await repo.add(new_campaign)
    print(f"✨ 저장 완료! 생성된 ID: {saved_campaign.id}")

    # 5. 조회 (Find)
    active_campaigns = await repo.get_active_campaigns()
    print(f"🔍 조회된 활성 캠페인 수: {len(active_campaigns)}")
    for camp in active_campaigns:
        print(f" - [{camp.name}] : {camp.message_template}")

if __name__ == "__main__":
    # 비동기 함수 실행을 위한 loop
    asyncio.run(main())