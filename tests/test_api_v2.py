# tests/test_api_v2.py
"""
API v2 통합 테스트

v2 API의 BaseResponse 형식을 검증합니다.
모든 응답이 success, data, error, message, timestamp 필드를 포함하는지 확인합니다.
"""
import pytest
from typing import List, Optional, Tuple
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.interface.api.routes_v2 import router as api_router_v2
from app.core.exceptions import CRMEngineException, DatabaseException
from app.application.interfaces import CampaignRepository, EventRepository, MessageRepository
from app.domain.models import Campaign, UserEvent, CrmMessage, EventType, CampaignStatus
from app.dependencies import get_campaign_repository, get_event_processor
from app.application.event_processor import EventProcessor


# ──────────────────────────────────────────────────
# 테스트용 FastAPI 앱
# ──────────────────────────────────────────────────

def create_test_app_v2() -> FastAPI:
    """v2 API 테스트용 앱"""
    test_app = FastAPI(title="Test CRM App v2")

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

    test_app.include_router(api_router_v2, prefix="/api/v2", tags=["CRM v2"])
    return test_app


app = create_test_app_v2()


# ──────────────────────────────────────────────────
# Fake Repository 정의 (v1과 동일)
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
        filtered = [c for c in self.store if status is None or c.status == status]
        filtered = list(reversed(filtered))

        start = 0
        if cursor:
            for i, c in enumerate(filtered):
                if c.id == cursor:
                    start = i + 1
                    break

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
# Fixtures
# ──────────────────────────────────────────────────

@pytest.fixture
def fake_campaign_repo():
    return FakeCampaignRepository()


@pytest.fixture
def fake_event_repo():
    return FakeEventRepository()


@pytest.fixture
def fake_message_repo():
    return FakeMessageRepository()


@pytest.fixture
def client(fake_campaign_repo, fake_event_repo, fake_message_repo):
    """TestClient with Fake Repositories"""
    def override_campaign_repo():
        return fake_campaign_repo

    def override_event_processor():
        return EventProcessor(
            repository=fake_campaign_repo,
            event_repo=fake_event_repo,
            message_repo=fake_message_repo
        )

    app.dependency_overrides[get_campaign_repository] = override_campaign_repo
    app.dependency_overrides[get_event_processor] = override_event_processor

    return TestClient(app)


# ──────────────────────────────────────────────────
# BaseResponse 형식 검증 헬퍼
# ──────────────────────────────────────────────────

def assert_base_response_success(response_json: dict):
    """BaseResponse 성공 응답 형식 검증"""
    assert "success" in response_json
    assert response_json["success"] is True
    assert "data" in response_json
    assert "error" in response_json
    assert response_json["error"] is None
    assert "message" in response_json
    assert "timestamp" in response_json


def assert_base_response_error(response_json: dict):
    """BaseResponse 에러 응답 형식 검증"""
    assert "success" in response_json
    assert response_json["success"] is False
    assert "data" in response_json
    assert response_json["data"] is None
    assert "error" in response_json
    assert response_json["error"] is not None
    assert "message" in response_json
    assert "timestamp" in response_json


# ──────────────────────────────────────────────────
# 테스트: POST /api/v2/events
# ──────────────────────────────────────────────────

class TestTrackEventV2:
    """이벤트 수신 API v2 테스트"""

    def test_track_event_success(self, client, fake_campaign_repo):
        """v2: 이벤트 처리 성공 시 BaseResponse 형식 확인"""
        # Given: 활성 캠페인 생성
        campaign = Campaign(
            id="c1",
            name="VIP Cart Promo",
            target_event=EventType.ADD_TO_CART,
            min_cart_value=50000,
            message_template="🎁 5천원 쿠폰",
            status=CampaignStatus.ACTIVE
        )
        fake_campaign_repo.store.append(campaign)

        # When: 이벤트 발생
        response = client.post("/api/v2/events", json={
            "user_id": "user_123",
            "event_type": "add_to_cart",
            "metadata": {"price": 60000}
        })

        # Then: BaseResponse 형식 검증
        assert response.status_code == 200
        data = response.json()

        assert_base_response_success(data)
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 1
        assert data["data"][0]["user_id"] == "user_123"
        assert data["data"][0]["content"] == "🎁 5천원 쿠폰"
        assert "메시지 생성" in data["message"]

    def test_track_event_no_match(self, client, fake_campaign_repo):
        """v2: 매칭되는 캠페인 없을 때 빈 배열 반환"""
        # Given: 로그인 캠페인만 있음
        campaign = Campaign(
            id="c1",
            name="Login Campaign",
            target_event=EventType.LOGIN,
            min_cart_value=0,
            message_template="환영합니다",
            status=CampaignStatus.ACTIVE
        )
        fake_campaign_repo.store.append(campaign)

        # When: 장바구니 이벤트 발생
        response = client.post("/api/v2/events", json={
            "user_id": "user_456",
            "event_type": "add_to_cart",
            "metadata": {"price": 30000}
        })

        # Then: 빈 배열이지만 BaseResponse 형식
        assert response.status_code == 200
        data = response.json()

        assert_base_response_success(data)
        assert data["data"] == []
        assert "0개 메시지" in data["message"]


# ──────────────────────────────────────────────────
# 테스트: POST /api/v2/campaigns
# ──────────────────────────────────────────────────

class TestCreateCampaignV2:
    """캠페인 생성 API v2 테스트"""

    def test_create_campaign_success(self, client):
        """v2: 캠페인 생성 성공 시 BaseResponse 형식 확인"""
        response = client.post("/api/v2/campaigns", json={
            "name": "Test Campaign",
            "target_event": "add_to_cart",
            "min_cart_value": 50000,
            "message_template": "쿠폰 발급"
        })

        assert response.status_code == 201
        data = response.json()

        assert_base_response_success(data)
        assert "id" in data["data"]
        assert data["data"]["id"].startswith("fake_id_")
        assert "성공" in data["message"]


# ──────────────────────────────────────────────────
# 테스트: GET /api/v2/campaigns
# ──────────────────────────────────────────────────

class TestListCampaignsV2:
    """캠페인 목록 조회 API v2 테스트"""

    def test_list_campaigns_success(self, client, fake_campaign_repo):
        """v2: 캠페인 목록 조회 성공"""
        # Given: 2개 캠페인
        for i in range(2):
            campaign = Campaign(
                id=f"c{i}",
                name=f"Campaign {i}",
                target_event=EventType.LOGIN,
                min_cart_value=0,
                message_template=f"Message {i}",
                status=CampaignStatus.ACTIVE
            )
            fake_campaign_repo.store.append(campaign)

        # When: 목록 조회
        response = client.get("/api/v2/campaigns")

        # Then: BaseResponse 형식
        assert response.status_code == 200
        data = response.json()

        assert_base_response_success(data)
        assert "items" in data["data"]
        assert len(data["data"]["items"]) == 2
        assert "조회 완료" in data["message"]


# ──────────────────────────────────────────────────
# 테스트: POST /api/v2/events/batch
# ──────────────────────────────────────────────────

class TestTrackEventBatchV2:
    """배치 이벤트 처리 API v2 테스트"""

    def test_batch_success(self, client, fake_campaign_repo):
        """v2: 배치 처리 성공"""
        # Given: 활성 캠페인
        campaign = Campaign(
            id="c1",
            name="Login Campaign",
            target_event=EventType.LOGIN,
            min_cart_value=0,
            message_template="환영",
            status=CampaignStatus.ACTIVE
        )
        fake_campaign_repo.store.append(campaign)

        # When: 배치 요청
        response = client.post("/api/v2/events/batch", json=[
            {"user_id": "user1", "event_type": "login", "metadata": {}},
            {"user_id": "user2", "event_type": "login", "metadata": {}}
        ])

        # Then: BaseResponse 형식
        assert response.status_code == 200
        data = response.json()

        assert_base_response_success(data)
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2
        assert "배치 처리 완료" in data["message"]
        assert "2개 이벤트" in data["message"]

    def test_batch_empty_list(self, client):
        """v2: 빈 배열 전송 시 에러 (BaseResponse 형식)"""
        response = client.post("/api/v2/events/batch", json=[])

        assert response.status_code == 400
        data = response.json()

        # HTTPException의 detail에 BaseResponse가 담겨 있음
        error_data = data.get("detail", data)
        assert_base_response_error(error_data)
        assert error_data["error"]["code"] == "VALIDATION_ERROR"
        assert "검증 실패" in error_data["message"]
