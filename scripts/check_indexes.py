"""
MongoDB 인덱스 확인 및 쿼리 실행 계획 분석 스크립트

사용법:
    PYTHONPATH=. python scripts/check_indexes.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def check_indexes():
    """MongoDB 인덱스를 확인하고 쿼리 실행 계획을 출력합니다."""
    # 로컬에서 실행 시 localhost 사용 및 Docker DB 이름 사용
    database_url = settings.DATABASE_URL.replace("mongo:27017", "localhost:27017")
    client = AsyncIOMotorClient(database_url)
    # Docker 컨테이너의 DB 이름 사용
    db_name = "clean_crm_db"
    db = client[db_name]

    collections = ["campaigns", "user_events", "crm_messages"]

    print("\n" + "=" * 60)
    print("MongoDB 인덱스 확인")
    print("=" * 60)

    for coll_name in collections:
        print(f"\n[Collection: {coll_name}]")

        coll = db[coll_name]
        # Motor에서는 list_indexes()를 사용
        cursor = coll.list_indexes()
        indexes = await cursor.to_list(length=None)

        for idx_info in indexes:
            idx_name = idx_info.get('name', 'N/A')
            idx_key = idx_info.get('key', {})
            print(f"  인덱스: {idx_name}")
            print(f"    키: {list(idx_key.items())}")
            if idx_info.get('unique'):
                print(f"    유니크: True")

    # explain() 예제
    print(f"\n{'=' * 60}")
    print("쿼리 실행 계획 (explain)")
    print(f"{'=' * 60}")

    campaigns = db["campaigns"]

    # 1. get_active_campaigns() 쿼리
    cursor = campaigns.find({"status": "active"})
    explain = await cursor.explain()
    print(f"\n[쿼리 1] find({{status: 'active'}})")
    winning_plan = explain.get('queryPlanner', {}).get('winningPlan', {})
    print(f"  실행 단계: {winning_plan.get('stage', 'N/A')}")

    # 인덱스 정보 추출
    def extract_index_name(plan):
        if 'indexName' in plan:
            return plan['indexName']
        if 'inputStage' in plan:
            return extract_index_name(plan['inputStage'])
        return None

    index_name = extract_index_name(winning_plan)
    if index_name:
        print(f"  인덱스 사용: {index_name}")
    else:
        print(f"  인덱스 사용: 없음 (COLLSCAN)")

    # 2. get_campaigns() 페이지네이션 쿼리
    cursor = campaigns.find({"status": "active"}).sort([("_id", -1)]).limit(20)
    explain = await cursor.explain()
    print(f"\n[쿼리 2] find({{status: 'active'}}).sort({{_id: -1}}).limit(20)")
    winning_plan = explain.get('queryPlanner', {}).get('winningPlan', {})
    print(f"  실행 단계: {winning_plan.get('stage', 'N/A')}")

    index_name = extract_index_name(winning_plan)
    if index_name:
        print(f"  인덱스 사용: {index_name}")
    else:
        print(f"  인덱스 사용: 없음 (COLLSCAN)")

    client.close()
    print("\n인덱스 확인 완료!\n")


if __name__ == "__main__":
    asyncio.run(check_indexes())
