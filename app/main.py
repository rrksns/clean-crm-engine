# app/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.infrastructure.db.connection import connect_to_mongo, get_db_client
from app.infrastructure.cache.redis_cache import connect_to_redis, close_redis
from app.interface.api.routes import router as api_router_v1
from app.interface.api.routes_v2 import router as api_router_v2
from app.core.exceptions import CRMEngineException, DatabaseException
from app.application.dtos import BaseResponse, success_response, error_response
from app.core.config import settings

# 로깅 설정 (환경별 LOG_LEVEL 적용)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 DB 연결
    await connect_to_mongo()
    # Redis 연결 (실패해도 앱은 시작됨)
    try:
        await connect_to_redis()
    except Exception as e:
        logger.warning(f"Redis 연결 실패, 캐시 없이 운영됩니다: {e}")
    yield
    # 앱 종료 시 Redis 연결 종료
    await close_redis()

app = FastAPI(
    title="Clean CRM Engine",
    description="이벤트 기반 마케팅 자동화 API",
    version="1.0.0",
    lifespan=lifespan
)


# ──────────────────────────────────────────────────
# 전역 예외 핸들러 (Global Exception Handlers)
# ──────────────────────────────────────────────────

@app.exception_handler(CRMEngineException)
async def crm_exception_handler(request: Request, exc: CRMEngineException):
    """
    커스텀 예외 처리
    Routes에서 처리되지 않은 도메인 예외를 여기서 잡습니다.
    """
    logger.error(f"CRM Exception: {exc.message}", exc_info=True)

    # 예외 타입에 따라 HTTP 상태 코드 결정
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, DatabaseException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": exc.code,
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    예상치 못한 모든 예외를 여기서 처리 (최후의 방어선)
    """
    logger.critical(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "서버에서 예기치 않은 오류가 발생했습니다",
            "details": None  # 보안상 상세 정보는 숨김
        }
    )


# ──────────────────────────────────────────────────
# 라우터 등록 (API Version Management)
# ──────────────────────────────────────────────────

# v1 API: 기존 형식 (List, dict 직접 반환)
# deprecated: v2 사용을 권장하지만 하위 호환성을 위해 유지
app.include_router(
    api_router_v1,
    prefix="/api/v1",
    tags=["CRM v1 (Deprecated)"],
    deprecated=True
)

# v2 API: BaseResponse 표준 형식
# 모든 엔드포인트가 일관된 success, data, error, message, timestamp 필드 제공
app.include_router(
    api_router_v2,
    prefix="/api/v2",
    tags=["CRM v2 (Recommended)"]
)

@app.get("/")
async def root():
    """
    API 루트 엔드포인트 - 서비스 정보 제공

    Returns:
        dict: 서비스 메타데이터 및 주요 엔드포인트 링크
    """
    return {
        "service": "Clean CRM Engine",
        "description": "이벤트 기반 마케팅 자동화 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": {
            "liveness": "/health/live",
            "readiness": "/health/ready"
        },
        "api": {
            "v1": "/api/v1 (deprecated)",
            "v2": "/api/v2 (recommended)"
        }
    }


@app.get("/health/live")
async def liveness_probe():
    """
    Liveness Probe - 애플리케이션이 살아있는지 확인

    Kubernetes liveness probe용 엔드포인트입니다.
    외부 의존성(DB, Redis 등)을 체크하지 않고, 애플리케이션이 크래시되지 않았는지만 확인합니다.

    Returns:
        dict: 항상 {"status": "alive"} 반환 (200 OK)
    """
    return {"status": "alive"}


@app.get("/health/ready", response_model=BaseResponse)
async def readiness_probe():
    """
    Readiness Probe - 트래픽을 받을 준비가 되었는지 확인

    Kubernetes readiness probe용 엔드포인트입니다.
    데이터베이스 연결 상태를 포함한 모든 의존성을 체크합니다.

    - 성공: 200 OK (모든 시스템 정상, 트래픽 수신 가능)
    - 실패: 503 Service Unavailable (의존성 문제, 트래픽 수신 불가)

    Returns:
        BaseResponse: 서비스 준비 상태 정보
    """
    readiness_status = {
        "service": "Clean CRM Engine",
        "version": "1.0.0",
        "status": "ready"
    }

    # DB 연결 상태 확인
    client = get_db_client()
    if client is None:
        # 클라이언트가 초기화되지 않음
        readiness_status["database"] = "not_initialized"
        readiness_status["status"] = "not_ready"
        logger.warning("Readiness check: Database client not initialized")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response(
                error_code="DB_NOT_INITIALIZED",
                error_message="데이터베이스가 초기화되지 않았습니다",
                message="서비스 준비 안됨"
            ).model_dump()
        )

    # DB Ping 테스트
    try:
        # MongoDB의 admin 명령으로 연결 상태 확인
        await client.admin.command('ping')
        readiness_status["database"] = "connected"
        logger.info("Readiness check: All systems operational")

        return success_response(
            data=readiness_status,
            message="트래픽 수신 준비 완료"
        )

    except Exception as e:
        # DB 연결 실패
        readiness_status["database"] = "disconnected"
        readiness_status["status"] = "not_ready"
        logger.error(f"Readiness check failed: {str(e)}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response(
                error_code="DB_CONNECTION_FAILED",
                error_message="데이터베이스 연결 실패",
                details=str(e),
                message="서비스 준비 안됨"
            ).model_dump()
        )