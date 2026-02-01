# app/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.infrastructure.db.connection import connect_to_mongo
from app.interface.api.routes import router as api_router
from app.core.exceptions import CRMEngineException, DatabaseException

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 DB 연결
    await connect_to_mongo()
    yield
    # 앱 종료 시 로직 (필요하면 추가)

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


# 라우터 등록 (Spring의 Component Scan 결과 등록과 유사)
# prefix="/api/v1" -> 모든 주소 앞에 /api/v1이 붙음
app.include_router(api_router, prefix="/api/v1", tags=["CRM"])

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "Clean CRM Engine"}