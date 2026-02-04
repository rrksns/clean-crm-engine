# app/interface/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging

from app.application.dtos import (
    EventRequest, MessageResponse, CampaignCreateRequest,
    CampaignResponse, PaginatedCampaignResponse, BaseResponse, success_response
)
from app.application.event_processor import EventProcessor
from app.dependencies import get_event_processor, get_campaign_repository
from app.application.interfaces import CampaignRepository
from app.domain.models import Campaign, CampaignStatus
from app.core.exceptions import (
    DatabaseException,
    ValidationException,
    DuplicateResourceException,
    CRMEngineException
)

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# --- 1. 이벤트 수신 API (메인 기능) ---
@router.post("/events", response_model=List[MessageResponse])
async def track_event(
        request: EventRequest,
        # @Autowired: 의존성 주입이 여기서 일어납니다!
        processor: EventProcessor = Depends(get_event_processor)
):
    """
    사용자 행동 이벤트를 수신하고, 조건에 맞는 캠페인 메시지를 반환합니다.

    Raises:
        HTTPException(500): 데이터베이스 에러
        HTTPException(400): 잘못된 요청 데이터
    """
    try:
        results = await processor.process_event(request)
        return results

    except DatabaseException as e:
        # DB 관련 에러 → 500 Internal Server Error
        logger.error(f"Database error in track_event: {e.message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": e.code,
                "message": "데이터베이스 처리 중 오류가 발생했습니다",
                "details": e.details
            }
        )

    except ValidationException as e:
        # 검증 에러 → 400 Bad Request
        logger.warning(f"Validation error in track_event: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.code,
                "message": e.message,
                "details": e.details
            }
        )

    except Exception as e:
        # 예상치 못한 에러 → 500 Internal Server Error
        logger.error(f"Unexpected error in track_event: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다"
            }
        )

# --- 2. 캠페인 등록 API (데이터 세팅용) ---
@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
async def create_campaign(
        request: CampaignCreateRequest,
        repo: CampaignRepository = Depends(get_campaign_repository)
):
    """
    마케터가 새로운 캠페인 규칙을 등록합니다.

    Raises:
        HTTPException(409): 중복된 캠페인
        HTTPException(500): 데이터베이스 에러
    """
    try:
        # DTO -> Domain 변환 (간단해서 여기서 처리하지만, 복잡하면 Service로 위임)
        new_campaign = Campaign(
            id="",  # DB 저장 시 생성됨
            name=request.name,
            target_event=request.target_event,
            min_cart_value=request.min_cart_value,
            message_template=request.message_template,
            status=CampaignStatus.ACTIVE
        )

        saved_campaign = await repo.add(new_campaign)
        logger.info(f"Campaign created successfully: {saved_campaign.id}")
        return {
            "id": saved_campaign.id,
            "message": "Campaign created successfully"
        }

    except DuplicateResourceException as e:
        # 중복 리소스 → 409 Conflict
        logger.warning(f"Duplicate campaign: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": e.code,
                "message": e.message,
                "details": e.details
            }
        )

    except DatabaseException as e:
        # DB 관련 에러 → 500 Internal Server Error
        logger.error(f"Database error in create_campaign: {e.message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": e.code,
                "message": "캠페인 생성 중 데이터베이스 오류가 발생했습니다",
                "details": e.details
            }
        )

    except Exception as e:
        # 예상치 못한 에러
        logger.error(f"Unexpected error in create_campaign: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다"
            }
        )

# --- 3. 캠페인 목록 조회 API (페이지네이션) ---
@router.get("/campaigns", response_model=BaseResponse)
async def list_campaigns(
        cursor: Optional[str] = Query(None, description="페이지네이션 커서 (마지막 항목의 ID)"),
        limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수 (1~100, 기본 20)"),
        campaign_status: Optional[CampaignStatus] = Query(None, alias="status", description="상태별 필터 (active/paused/ended)"),
        repo: CampaignRepository = Depends(get_campaign_repository)
):
    """
    캠페인 목록을 커서 기반 페이지네이션으로 조회합니다.

    - 기본 정렬: 등록 일시 내림차순 (최신 우선)
    - 커서: 응답의 next_cursor 값을 다음 요청에 전달
    """
    try:
        campaigns, next_cursor = await repo.get_campaigns(
            cursor=cursor,
            limit=limit,
            status=campaign_status
        )

        # Domain → Response DTO 변환
        items = [
            CampaignResponse(
                id=c.id,
                name=c.name,
                target_event=c.target_event,
                min_cart_value=c.min_cart_value,
                message_template=c.message_template,
                status=c.status
            ) for c in campaigns
        ]

        return success_response(
            data=PaginatedCampaignResponse(
                items=items,
                next_cursor=next_cursor,
                has_next=next_cursor is not None,
                limit=limit
            ),
            message="캠페인 목록 조회 완료"
        )

    except ValidationException as e:
        logger.warning(f"Validation error in list_campaigns: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": e.code, "message": e.message, "details": e.details}
        )

    except DatabaseException as e:
        logger.error(f"Database error in list_campaigns: {e.message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": e.code, "message": "캠페인 목록 조회 중 DB 오류", "details": e.details}
        )

    except Exception as e:
        logger.error(f"Unexpected error in list_campaigns: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": "서버 내부 오류가 발생했습니다"}
        )


# --- 4. 배치 이벤트 처리 API (성능 최적화) ---
@router.post("/events/batch", response_model=List[MessageResponse])
async def track_event_batch(
        requests: List[EventRequest],  # 리스트로 받습니다!
        processor: EventProcessor = Depends(get_event_processor)
):
    """
    [성능 최적화] 대량의 이벤트를 한 번에 처리합니다. (Batch Processing)

    단건 API 대비 약 20배 성능 향상:
    - DB 조회: N회 → 1회
    - 네트워크 오버헤드: N회 → 1회
    - 캠페인 매칭: 메모리에서 일괄 처리

    Raises:
        HTTPException(400): 빈 요청 리스트
        HTTPException(500): 데이터베이스 에러
    """
    try:
        # 검증: 빈 리스트 체크
        if not requests:
            raise ValidationException(
                field="requests",
                reason="최소 1개 이상의 이벤트가 필요합니다"
            )

        results = await processor.process_event_batch(requests)
        logger.info(f"Batch processed {len(requests)} events, generated {len(results)} messages")
        return results

    except ValidationException as e:
        # 검증 에러
        logger.warning(f"Validation error in track_event_batch: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.code,
                "message": e.message,
                "details": e.details
            }
        )

    except DatabaseException as e:
        # DB 관련 에러
        logger.error(f"Database error in track_event_batch: {e.message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": e.code,
                "message": "배치 처리 중 데이터베이스 오류가 발생했습니다",
                "details": e.details
            }
        )

    except Exception as e:
        # 예상치 못한 에러
        logger.error(f"Unexpected error in track_event_batch: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다"
            }
        )