# app/main.py (수정)
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.infrastructure.db.connection import connect_to_mongo
from app.interface.api.routes import router as api_router # 추가

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 DB 연결
    await connect_to_mongo()
    yield
    # 앱 종료 시 로직 (필요하면 추가)

app = FastAPI(title="Clean CRM Engine", lifespan=lifespan)

# 라우터 등록 (Spring의 Component Scan 결과 등록과 유사)
# prefix="/api/v1" -> 모든 주소 앞에 /api/v1이 붙음
app.include_router(api_router, prefix="/api/v1", tags=["CRM"])

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "Clean CRM Engine"}