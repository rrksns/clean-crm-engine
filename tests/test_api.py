# tests/test_api.py
"""
API 통합 테스트

FastAPI TestClient + FakeRepository를 사용하여 실제 HTTP 흐름을 검증합니다.
MongoDB 없이도 엔드포인트의 요청·응답·에러 핸들링을 테스트할 수 있습니다.
"""
import pytest
from typing import List, Optional, Tuple
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.interface.api.routes import router as api_router
from app.core.exceptions import CRMEngineException, DatabaseException
from app.application.interfaces import CampaignRepository, EventRepository, MessageRepository
from app.domain.models import Campaign, UserEvent, CrmMessage, EventType, CampaignStatus
from app.dependencies import get_campaign_repository, get_event_processor
from app.application.event_processor import EventProcessor


# ──────────────────────────────────────────────────
# 테스트용 FastAPI 앱 (lifespan 없음 → MongoDB 연결 불필요)
# ──────────────────────────────────────────────────

def create_test_app() -> FastAPI:
    """MongoDB 연결 없이 테스트할 수 있는 앱"""
    test_app = FastAPI(title="Test CRM App")

    @test_app.exception_handler(CRMEngineException)
    async def crm_exception_handler(request: Request, exc: CRMEngineException):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(exc, DatabaseException):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(
            status_code=status_code,
            content={"error_code": exc.code, "message": exc.message, "details": exc.details}
        )

    @test_app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error_code": "INTERNAL_SERVER_ERROR", "message": "서버 내부 오류"}
        )

    test_app.include_router(api_router, prefix="/api/v1", tags=["CRM"])
    return test_app


app = create_test_app()


# ──────────────────────────────────────────────────
# Fake Repository 정의
# ──────────────────────────────────────────────────

class FakeCampaignRepository(CampaignRepository):
    def __init__(self):
        self.store: List[Campaign] = []

    async def add(self, campaign: Campaign) -> Campaign:
        campaign.id = f"fake_id_{len(self.store)}"
        self.store.append(campaign)
        return campaign

    async def get_active_campaigns(self) -> List[Campaign]:
        return [c for c in self.store if c.status == CampaignStatus.ACTIVE]

    async def add_all(self, campaigns: List[Campaign]) -> bool:
        self.store.extend(campaigns)
        return bool(campaigns)

    async def get_campaigns(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        status: Optional[CampaignStatus] = None
    ) -> Tuple[List[Campaign], Optional[str]]:
        # 상태 필터
        filtered = [c for c in self.store if status is None or c.status == status]

        # 등록 순서 역방향 (최신 우선) — store 순서가 삽입 순서
        filtered = list(reversed(filtered))

        # 커서 적용: cursor ID와 동일한 항목 이후부터
        start = 0
        if cursor:
            for i, c in enumerate(filtered):
                if c.id == cursor:
                    start = i + 1
                    break

        # limit + 1개 조회 후 has_next 판단
        page = filtered[start:start + limit + 1]
        has_next = len(page) > limit
        if has_next:
            page = page[:limit]

        next_cursor = page[-1].id if has_next else None
        return page, next_cursor


class FakeEventRepository(EventRepository):
    def __init__(self):
        self.store: List[UserEvent] = []

    async def save(self, event: UserEvent) -> UserEvent:
        self.store.append(event)
        return event

    async def save_all(self, events: List[UserEvent]) -> bool:
        self.store.extend(events)
        return bool(events)


class FakeMessageRepository(MessageRepository):
    def __init__(self):
        self.store: List[CrmMessage] = []

    async def save(self, message: CrmMessage) -> CrmMessage:
        self.store.append(message)
        return message

    async def save_all(self, messages: List[CrmMessage]) -> bool:
        self.store.extend(messages)
        return bool(messages)


# ──────────────────────────────────────────────────
# Fixture: 테스트별로 깨끗한 Fake 저장소와 TestClient 생성
# ──────────────────────────────────────────────────

@pytest.fixture
def fake_repos():
    """각 테스트마다 신선한 Fake 저장소를 생성"""
    return {
        "campaign": FakeCampaignRepository(),
        "event": FakeEventRepository(),
        "message": FakeMessageRepository(),
    }


@pytest.fixture
def client(fake_repos):
    """dependency_overrides를 활용하여 Fake로 교체된 TestClient"""
    fake_campaign_repo = fake_repos["campaign"]
    fake_event_repo = fake_repos["event"]
    fake_message_repo = fake_repos["message"]

    # FastAPI 의존성 오버라이드
    app.dependency_overrides[get_campaign_repository] = lambda: fake_campaign_repo
    app.dependency_overrides[get_event_processor] = lambda: EventProcessor(
        repository=fake_campaign_repo,
        event_repo=fake_event_repo,
        message_repo=fake_message_repo
    )

    with TestClient(app) as c:
        yield c

    # 테스트 후 오버라이드 초기화
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_campaigns(client, fake_repos):
    """캠페인이 미리 세팅된 client"""
    import asyncio

    async def setup():
        repo = fake_repos["campaign"]
        await repo.add(Campaign(
            id="", name="VIP Cart Promotion",
            target_event=EventType.ADD_TO_CART,
            min_cart_value=50000,
            message_template="🎁 VIP 할인 쿠폰 발급!",
            status=CampaignStatus.ACTIVE
        ))
        await repo.add(Campaign(
            id="", name="Login Bonus",
            target_event=EventType.LOGIN,
            min_cart_value=0,
            message_template="🎉 로그인 포인트 100P 적립!",
            status=CampaignStatus.ACTIVE
        ))
        await repo.add(Campaign(
            id="", name="Paused Campaign",
            target_event=EventType.ADD_TO_CART,
            min_cart_value=0,
            message_template="이건 보내지 않음",
            status=CampaignStatus.PAUSED
        ))

    asyncio.get_event_loop().run_until_complete(setup())
    return client


# ──────────────────────────────────────────────────
# 테스트: POST /api/v1/campaigns (캠페인 등록)
# ──────────────────────────────────────────────────

class TestCreateCampaign:

    def test_create_campaign_success(self, client):
        """캠페인 등록 성공 → 201 Created"""
        response = client.post("/api/v1/campaigns", json={
            "name": "New Campaign",
            "target_event": "add_to_cart",
            "min_cart_value": 30000,
            "message_template": "테스트 메시지"
        })

        assert response.status_code == 201
        body = response.json()
        assert "id" in body
        assert body["message"] == "Campaign created successfully"

    def test_create_campaign_missing_field(self, client):
        """필수 필드 누락 → 422 Validation Error (Pydantic)"""
        response = client.post("/api/v1/campaigns", json={
            "name": "Missing Fields"
            # target_event, message_template 누락
        })

        assert response.status_code == 422

    def test_create_campaign_invalid_event_type(self, client):
        """유효하지 않은 event_type → 422"""
        response = client.post("/api/v1/campaigns", json={
            "name": "Bad Event",
            "target_event": "invalid_event_type",
            "message_template": "테스트"
        })

        assert response.status_code == 422


# ──────────────────────────────────────────────────
# 테스트: POST /api/v1/events (단건 이벤트 처리)
# ──────────────────────────────────────────────────

class TestTrackEvent:

    def test_track_event_matching(self, client_with_campaigns, fake_repos):
        """캠페인 조건 충족 이벤트 → 메시지 반환"""
        response = client_with_campaigns.post("/api/v1/events", json={
            "user_id": "user_1",
            "event_type": "add_to_cart",
            "metadata": {"price": 60000}
        })

        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 1
        assert messages[0]["user_id"] == "user_1"
        assert messages[0]["campaign_name"] == "VIP Cart Promotion"

        # 이벤트·메시지가 저장소에 기록되었는지 확인
        assert len(fake_repos["event"].store) == 1
        assert len(fake_repos["message"].store) == 1

    def test_track_event_no_match(self, client_with_campaigns, fake_repos):
        """캠페인 조건 미충족 (금액 부족) → 빈 리스트"""
        response = client_with_campaigns.post("/api/v1/events", json={
            "user_id": "user_2",
            "event_type": "add_to_cart",
            "metadata": {"price": 10000}  # min_cart_value 50000 미충족
        })

        assert response.status_code == 200
        assert response.json() == []

        # 이벤트는 저장되지만 메시지는 없음
        assert len(fake_repos["event"].store) == 1
        assert len(fake_repos["message"].store) == 0

    def test_track_event_login(self, client_with_campaigns):
        """로그인 이벤트 → Login Bonus 메시지"""
        response = client_with_campaigns.post("/api/v1/events", json={
            "user_id": "user_3",
            "event_type": "login",
            "metadata": {}
        })

        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 1
        assert messages[0]["campaign_name"] == "Login Bonus"

    def test_track_event_paused_campaign_ignored(self, client_with_campaigns):
        """PAUSED 상태 캠페인은 매칭되지 않음"""
        # view_product 이벤트는 활성 캠페인 중 어디에도 해당하지 않음
        response = client_with_campaigns.post("/api/v1/events", json={
            "user_id": "user_4",
            "event_type": "view_product",
            "metadata": {}
        })

        assert response.status_code == 200
        assert response.json() == []

    def test_track_event_invalid_body(self, client_with_campaigns):
        """잘못된 요청 본문 → 422"""
        response = client_with_campaigns.post("/api/v1/events", json={
            "user_id": "user_5"
            # event_type 누락
        })

        assert response.status_code == 422


# ──────────────────────────────────────────────────
# 테스트: POST /api/v1/events/batch (배치 이벤트 처리)
# ──────────────────────────────────────────────────

class TestTrackEventBatch:

    def test_batch_mixed_events(self, client_with_campaigns, fake_repos):
        """다양한 이벤트 혼합 배치 처리"""
        payload = [
            # 조건 충족 (장바구니 50k+)
            {"user_id": "u1", "event_type": "add_to_cart", "metadata": {"price": 70000}},
            # 조건 미충족 (장바구니 10k)
            {"user_id": "u2", "event_type": "add_to_cart", "metadata": {"price": 10000}},
            # 로그인 (조건 충족)
            {"user_id": "u3", "event_type": "login", "metadata": {}},
            # 상품 조회 (매칭 캠페인 없음)
            {"user_id": "u4", "event_type": "view_product", "metadata": {}},
        ]

        response = client_with_campaigns.post("/api/v1/events/batch", json=payload)

        assert response.status_code == 200
        messages = response.json()
        # u1 → VIP 쿠폰, u3 → Login Bonus = 2개
        assert len(messages) == 2

        # 이벤트 저장: 4개, 메시지 저장: 2개
        assert len(fake_repos["event"].store) == 4
        assert len(fake_repos["message"].store) == 2

    def test_batch_empty_list(self, client_with_campaigns):
        """빈 배치 → 400 Bad Request"""
        response = client_with_campaigns.post("/api/v1/events/batch", json=[])

        assert response.status_code == 400
        assert response.json()["detail"]["error_code"] == "VALIDATION_ERROR"

    def test_batch_single_event(self, client_with_campaigns, fake_repos):
        """단일 이벤트를 배치로 처리"""
        response = client_with_campaigns.post("/api/v1/events/batch", json=[
            {"user_id": "solo", "event_type": "login", "metadata": {}}
        ])

        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 1
        assert messages[0]["user_id"] == "solo"

    def test_batch_all_no_match(self, client_with_campaigns, fake_repos):
        """모든 이벤트가 조건 미충족"""
        payload = [
            {"user_id": f"u{i}", "event_type": "view_product", "metadata": {}}
            for i in range(5)
        ]

        response = client_with_campaigns.post("/api/v1/events/batch", json=payload)

        assert response.status_code == 200
        assert response.json() == []

        # 이벤트는 저장되지만 메시지는 없음
        assert len(fake_repos["event"].store) == 5
        assert len(fake_repos["message"].store) == 0

    def test_batch_invalid_event_type(self, client_with_campaigns):
        """유효하지 않은 event_type이 포함 → 422"""
        response = client_with_campaigns.post("/api/v1/events/batch", json=[
            {"user_id": "u1", "event_type": "not_a_valid_type", "metadata": {}}
        ])

        assert response.status_code == 422


# ──────────────────────────────────────────────────
# 테스트: GET /api/v1/campaigns (캠페인 목록 페이지네이션)
# ──────────────────────────────────────────────────

class TestListCampaigns:

    def test_list_campaigns_empty(self, client):
        """캠페인이 없을 때 → 빈 리스트"""
        response = client.get("/api/v1/campaigns")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["items"] == []
        assert body["data"]["has_next"] is False
        assert body["data"]["next_cursor"] is None

    def test_list_campaigns_basic(self, client_with_campaigns):
        """3개 캠페인 조회 → 전체 반환"""
        response = client_with_campaigns.get("/api/v1/campaigns")
        assert response.status_code == 200
        assert len(response.json()["data"]["items"]) == 3

    def test_list_campaigns_with_limit(self, client_with_campaigns):
        """limit=2 → 2개 반환, has_next=True"""
        response = client_with_campaigns.get("/api/v1/campaigns?limit=2")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["items"]) == 2
        assert data["has_next"] is True
        assert data["next_cursor"] is not None

    def test_list_campaigns_pagination_flow(self, client_with_campaigns):
        """전체 페이지네이션 흐름: 페이지1 → 페이지2"""
        # 페이지 1
        r1 = client_with_campaigns.get("/api/v1/campaigns?limit=2")
        d1 = r1.json()["data"]
        assert len(d1["items"]) == 2
        assert d1["has_next"] is True

        # 페이지 2 (cursor 사용)
        r2 = client_with_campaigns.get(f"/api/v1/campaigns?limit=2&cursor={d1['next_cursor']}")
        d2 = r2.json()["data"]
        assert len(d2["items"]) == 1    # 남은 1개
        assert d2["has_next"] is False
        assert d2["next_cursor"] is None

        # 중복 없음 확인
        ids_p1 = {item["id"] for item in d1["items"]}
        ids_p2 = {item["id"] for item in d2["items"]}
        assert ids_p1.isdisjoint(ids_p2)

    def test_list_campaigns_filter_by_status(self, client_with_campaigns):
        """status=active 필터 → PAUSED 제외"""
        response = client_with_campaigns.get("/api/v1/campaigns?status=active")
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert all(item["status"] == "active" for item in items)
        assert len(items) == 2  # client_with_campaigns에서 ACTIVE 2개

    def test_list_campaigns_invalid_limit(self, client):
        """limit=0 또는 limit=200 → 422 (FastAPI Query 검증)"""
        r1 = client.get("/api/v1/campaigns?limit=0")
        assert r1.status_code == 422

        r2 = client.get("/api/v1/campaigns?limit=200")
        assert r2.status_code == 422
