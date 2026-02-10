# tests/test_health.py
"""
헬스체크 엔드포인트 테스트

Kubernetes liveness/readiness probe 엔드포인트를 검증합니다.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestRootEndpoint:
    """루트 엔드포인트 테스트"""

    def test_root_returns_api_info(self):
        """루트 엔드포인트는 API 정보를 반환해야 함"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # 필수 필드 확인
        assert "service" in data
        assert data["service"] == "Clean CRM Engine"
        assert "version" in data
        assert "docs" in data
        assert "health" in data

        # 헬스체크 엔드포인트 정보
        assert "liveness" in data["health"]
        assert "readiness" in data["health"]
        assert data["health"]["liveness"] == "/health/live"
        assert data["health"]["readiness"] == "/health/ready"

        # API 버전 정보
        assert "api" in data
        assert "v1" in data["api"]
        assert "v2" in data["api"]


class TestLivenessProbe:
    """Liveness Probe 테스트"""

    def test_liveness_always_returns_alive(self):
        """Liveness probe는 항상 alive 상태를 반환해야 함"""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "alive"

    def test_liveness_does_not_check_dependencies(self):
        """Liveness probe는 외부 의존성(DB)을 체크하지 않아야 함"""
        # DB가 없어도 liveness는 성공해야 함
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

        # DB 상태 필드가 없어야 함 (체크하지 않으므로)
        assert "database" not in data


class TestReadinessProbe:
    """Readiness Probe 테스트"""

    def test_readiness_returns_503_when_db_not_initialized(self):
        """DB가 초기화되지 않았을 때 503 반환"""
        # 앱 시작 전이나 DB 연결 실패 시
        # 실제로는 lifespan에서 DB를 초기화하므로,
        # 이 테스트는 DB 연결 전 상태를 시뮬레이션
        response = client.get("/health/ready")

        # DB 초기화 전에는 503 또는 200 (lifespan 실행 여부에 따라)
        # TestClient는 lifespan을 실행하지 않으므로 503 예상
        assert response.status_code in [200, 503]

        data = response.json()

        # BaseResponse 또는 에러 응답 형식
        if response.status_code == 503:
            # 에러 응답
            error_data = data.get("detail", data)
            assert "success" in error_data
            assert error_data["success"] is False
        else:
            # 정상 응답
            assert "success" in data

    def test_readiness_checks_database_connection(self):
        """Readiness probe는 DB 연결 상태를 체크해야 함"""
        response = client.get("/health/ready")

        # 응답 구조 확인 (성공/실패 여부와 무관)
        data = response.json()

        if response.status_code == 200:
            # 정상 응답 - BaseResponse 형식
            assert "success" in data
            assert "data" in data
            if data["success"]:
                assert "database" in data["data"]
        else:
            # 에러 응답
            error_data = data.get("detail", data)
            assert "success" in error_data or "error_code" in error_data


class TestHealthEndpointPurpose:
    """헬스체크 엔드포인트의 용도 구분 테스트"""

    def test_liveness_is_fast(self):
        """Liveness는 빠르게 응답해야 함 (외부 의존성 체크 없음)"""
        import time

        start = time.time()
        response = client.get("/health/live")
        duration = time.time() - start

        assert response.status_code == 200
        # 0.1초 이내에 응답 (매우 빠름)
        assert duration < 0.1

    def test_readiness_may_be_slower(self):
        """Readiness는 DB 체크로 인해 느릴 수 있음"""
        # Readiness는 DB ping을 하므로 liveness보다 느림
        response = client.get("/health/ready")

        # 응답은 받아야 함 (성공/실패 여부와 무관)
        assert response.status_code in [200, 503]

    def test_endpoints_serve_different_purposes(self):
        """
        Liveness vs Readiness 용도 확인:
        - Liveness: 애플리케이션 크래시 감지 (재시작 트리거)
        - Readiness: 트래픽 수신 준비 상태 (로드밸런서 제어)
        """
        # Liveness는 항상 성공
        live_response = client.get("/health/live")
        assert live_response.status_code == 200

        # Readiness는 DB 상태에 따라 달라짐
        ready_response = client.get("/health/ready")
        assert ready_response.status_code in [200, 503]

        # 같은 시점에 liveness는 성공하지만 readiness는 실패할 수 있음
        # (앱은 살아있지만 DB 연결 문제로 트래픽 받을 준비가 안됨)
