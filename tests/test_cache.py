# tests/test_cache.py
"""
Phase 3-2: Redis 캐시 레이어 테스트

테스트 목록:
1. test_cache_miss_returns_none — 빈 캐시에서 조회 시 None 반환
2. test_cache_set_and_get_roundtrip — 캠페인 직렬화/역직렬화 검증
3. test_cache_ttl_is_300_seconds — TTL이 300초로 설정되는지 확인
4. test_cache_invalidation_after_delete — 무효화 후 캐시가 삭제되는지 확인
5. test_cache_none_graceful_fallback — cache=None일 때 예외 없이 통과
"""
import asyncio
from typing import Optional, List
from app.application.interfaces import CacheService
from app.infrastructure.db.repositories import MongoCampaignRepository
from app.domain.models import Campaign, EventType, CampaignStatus


# ──────────────────────────────────────────────────
# Fake Cache Service (테스트용)
# ──────────────────────────────────────────────────

class FakeCacheService(CacheService):
    """
    테스트용 가짜 캐시 서비스.

    특징:
    - 메모리 딕셔너리 기반 (in-memory)
    - TTL 값을 ttl_store에 기록 (검증용)
    - 삭제된 키를 delete_log에 기록 (검증용)
    """

    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttl_store: dict[str, int] = {}  # TTL 값 기록
        self.delete_log: list[str] = []  # 삭제된 키 기록

    async def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    async def set(self, key: str, value: str, ttl: int) -> None:
        self.store[key] = value
        self.ttl_store[key] = ttl

    async def delete(self, key: str) -> None:
        if key in self.store:
            del self.store[key]
        self.delete_log.append(key)


# ──────────────────────────────────────────────────
# 테스트 케이스
# ──────────────────────────────────────────────────

def test_cache_miss_returns_none():
    """
    테스트 1: 빈 캐시에서 조회 시 None 반환
    """
    async def run():
        # Given: 빈 캐시를 가진 Repository
        cache = FakeCacheService()
        repo = MongoCampaignRepository(cache=cache)

        # When: 캐시 조회
        result = await repo._get_from_cache()

        # Then: None 반환
        assert result is None
        print("✅ 테스트 1 통과: 캐시 미스 시 None 반환")

    asyncio.run(run())


def test_cache_set_and_get_roundtrip():
    """
    테스트 2: 캠페인 직렬화/역직렬화 검증

    확인 사항:
    - id, name, EventType(Enum), CampaignStatus(Enum) 모두 정상 복원
    """
    async def run():
        # Given: 캠페인 2개
        campaigns = [
            Campaign(
                id="camp_001",
                name="VIP 프로모션",
                target_event=EventType.ADD_TO_CART,
                min_cart_value=50000,
                message_template="🎁 할인 쿠폰!",
                status=CampaignStatus.ACTIVE
            ),
            Campaign(
                id="camp_002",
                name="신규 회원 환영",
                target_event=EventType.LOGIN,
                min_cart_value=0,
                message_template="환영합니다!",
                status=CampaignStatus.ACTIVE
            )
        ]

        # When: 캐시에 저장 후 조회
        cache = FakeCacheService()
        repo = MongoCampaignRepository(cache=cache)

        await repo._set_to_cache(campaigns)
        result = await repo._get_from_cache()

        # Then: 데이터가 정확히 복원됨
        assert result is not None
        assert len(result) == 2

        # 첫 번째 캠페인 검증
        assert result[0].id == "camp_001"
        assert result[0].name == "VIP 프로모션"
        assert result[0].target_event == EventType.ADD_TO_CART
        assert result[0].status == CampaignStatus.ACTIVE

        # 두 번째 캠페인 검증
        assert result[1].id == "camp_002"
        assert result[1].name == "신규 회원 환영"
        assert result[1].target_event == EventType.LOGIN

        print("✅ 테스트 2 통과: 직렬화/역직렬화 정상 동작")

    asyncio.run(run())


def test_cache_ttl_is_300_seconds():
    """
    테스트 3: TTL이 300초(5분)로 설정되는지 확인
    """
    async def run():
        # Given: 캠페인 1개
        campaigns = [
            Campaign(
                id="camp_ttl",
                name="TTL 테스트",
                target_event=EventType.PURCHASE,
                min_cart_value=0,
                message_template="감사합니다",
                status=CampaignStatus.ACTIVE
            )
        ]

        # When: 캐시에 저장
        cache = FakeCacheService()
        repo = MongoCampaignRepository(cache=cache)

        await repo._set_to_cache(campaigns)

        # Then: TTL이 300초로 설정됨
        from app.infrastructure.db.repositories import ACTIVE_CAMPAIGNS_CACHE_KEY
        assert ACTIVE_CAMPAIGNS_CACHE_KEY in cache.ttl_store
        assert cache.ttl_store[ACTIVE_CAMPAIGNS_CACHE_KEY] == 300

        print("✅ 테스트 3 통과: TTL이 300초로 설정됨")

    asyncio.run(run())


def test_cache_invalidation_after_delete():
    """
    테스트 4: 무효화 후 캐시가 삭제되는지 확인
    """
    async def run():
        # Given: 캐시에 데이터 저장
        campaigns = [
            Campaign(
                id="camp_inv",
                name="무효화 테스트",
                target_event=EventType.VIEW_PRODUCT,
                min_cart_value=0,
                message_template="조회 감사",
                status=CampaignStatus.ACTIVE
            )
        ]

        cache = FakeCacheService()
        repo = MongoCampaignRepository(cache=cache)

        await repo._set_to_cache(campaigns)

        # When: 캐시 무효화
        await repo._invalidate_cache()

        # Then: 캐시에서 삭제됨
        result = await repo._get_from_cache()
        assert result is None

        # 삭제 로그 확인
        from app.infrastructure.db.repositories import ACTIVE_CAMPAIGNS_CACHE_KEY
        assert ACTIVE_CAMPAIGNS_CACHE_KEY in cache.delete_log

        print("✅ 테스트 4 통과: 캐시 무효화 정상 동작")

    asyncio.run(run())


def test_cache_none_graceful_fallback():
    """
    테스트 5: cache=None일 때 예외 없이 정상 동작
    """
    async def run():
        # Given: cache=None인 Repository
        repo = MongoCampaignRepository(cache=None)

        # When: 캐시 헬퍼 메서드 호출
        result_get = await repo._get_from_cache()
        await repo._set_to_cache([])
        await repo._invalidate_cache()

        # Then: 예외 없이 통과
        assert result_get is None
        print("✅ 테스트 5 통과: cache=None일 때 graceful fallback")

    asyncio.run(run())


# ──────────────────────────────────────────────────
# 전체 테스트 실행
# ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 3-2: Redis 캐시 레이어 테스트")
    print("=" * 60 + "\n")

    test_cache_miss_returns_none()
    test_cache_set_and_get_roundtrip()
    test_cache_ttl_is_300_seconds()
    test_cache_invalidation_after_delete()
    test_cache_none_graceful_fallback()

    print("\n" + "=" * 60)
    print("🎉 모든 캐시 테스트 통과! (5/5)")
    print("=" * 60 + "\n")
