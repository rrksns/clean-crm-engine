# app/application/dtos.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional, Generic, TypeVar, List
from datetime import datetime
from app.domain.models import EventType, CampaignStatus

# Generic 타입 변수 (어떤 타입이든 담을 수 있도록)
T = TypeVar('T')

# 1. 프론트엔드에서 보낼 이벤트 요청 (Request DTO)
class EventRequest(BaseModel):
    user_id: str
    event_type: EventType
    metadata: Dict[str, Any] = {}

# 2. 마케터가 캠페인을 등록할 때 쓸 요청 (Request DTO)
class CampaignCreateRequest(BaseModel):
    name: str
    target_event: EventType
    min_cart_value: Optional[int] = 0
    message_template: str

# 3. 결과로 돌려줄 메시지 응답 (Response DTO)
class MessageResponse(BaseModel):
    user_id: str
    content: str
    campaign_name: str


# 4. 단일 캠페인 응답 (Response DTO)
class CampaignResponse(BaseModel):
    id: str
    name: str
    target_event: EventType
    min_cart_value: int
    message_template: str
    status: CampaignStatus

# 5. 페이지네이션된 캠페인 목록 응답 (Response DTO)
class PaginatedCampaignResponse(BaseModel):
    items: List[CampaignResponse]
    next_cursor: Optional[str] = None   # 다음 페이지 없으면 None
    has_next: bool
    limit: int


# ──────────────────────────────────────────────────
# 표준 API 응답 형식 (Standard Response Format)
# ──────────────────────────────────────────────────

class BaseResponse(BaseModel, Generic[T]):
    """
    모든 API 응답의 표준 형식

    실무에서는 프론트엔드와 백엔드 간의 일관된 응답 형식이 필수입니다.
    성공/실패 여부, 데이터, 에러 정보, 타임스탬프를 표준화하여 제공합니다.

    Examples:
        # 성공 응답
        BaseResponse[List[MessageResponse]](
            success=True,
            data=[...],
            message="이벤트 처리 완료"
        )

        # 에러 응답
        BaseResponse[None](
            success=False,
            error={"code": "DB_ERROR", "message": "..."},
            message="처리 중 오류 발생"
        )
    """
    success: bool = Field(..., description="요청 성공 여부")
    data: Optional[T] = Field(None, description="응답 데이터 (성공 시)")
    error: Optional[Dict[str, Any]] = Field(None, description="에러 정보 (실패 시)")
    message: Optional[str] = Field(None, description="추가 메시지")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="응답 생성 시간 (ISO 8601)"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {"id": "123", "name": "Example"},
            "error": None,
            "message": "처리 완료",
            "timestamp": "2026-02-02T10:30:00"
        }
    })


# 편의 함수: 성공 응답 생성
def success_response(
    data: Any = None,
    message: Optional[str] = None
) -> BaseResponse:
    """성공 응답을 간편하게 생성합니다"""
    return BaseResponse(
        success=True,
        data=data,
        error=None,
        message=message
    )


# 편의 함수: 에러 응답 생성
def error_response(
    error_code: str,
    error_message: str,
    details: Optional[Any] = None,
    message: Optional[str] = None
) -> BaseResponse:
    """에러 응답을 간편하게 생성합니다"""
    return BaseResponse(
        success=False,
        data=None,
        error={
            "code": error_code,
            "message": error_message,
            "details": details
        },
        message=message
    )