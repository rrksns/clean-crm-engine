# test_phase2.py
"""
Phase 2 작업 검증 스크립트

1. BaseResponse 모델 동작 확인
2. 헬스체크 API 강화 확인 (실제 서버 필요)
"""
from datetime import datetime
from app.application.dtos import (
    BaseResponse,
    success_response,
    error_response,
    MessageResponse
)


def test_base_response_model():
    """BaseResponse 모델 동작 테스트"""
    print("🧪 Test 1: BaseResponse 모델 동작 확인")
    print("=" * 60)

    # 테스트 1-1: 성공 응답 생성
    print("  [1-1] 성공 응답 생성...")
    success_resp = success_response(
        data={"user_id": "user_123", "status": "processed"},
        message="이벤트 처리 완료"
    )

    assert success_resp.success is True
    assert success_resp.data is not None
    assert success_resp.error is None
    assert success_resp.message == "이벤트 처리 완료"
    assert success_resp.timestamp is not None
    print(f"  ✅ 성공 응답: {success_resp.model_dump_json(indent=2)[:100]}...")

    # 테스트 1-2: 에러 응답 생성
    print("  [1-2] 에러 응답 생성...")
    error_resp = error_response(
        error_code="VALIDATION_ERROR",
        error_message="잘못된 요청 데이터",
        details={"field": "user_id", "reason": "필수 항목"},
        message="요청 처리 실패"
    )

    assert error_resp.success is False
    assert error_resp.data is None
    assert error_resp.error is not None
    assert error_resp.error["code"] == "VALIDATION_ERROR"
    assert error_resp.message == "요청 처리 실패"
    print(f"  ✅ 에러 응답: code={error_resp.error['code']}")

    # 테스트 1-3: Generic 타입 테스트 (리스트 데이터)
    print("  [1-3] Generic 타입 테스트...")
    list_resp = success_response(
        data=[
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ],
        message="목록 조회 완료"
    )

    assert isinstance(list_resp.data, list)
    assert len(list_resp.data) == 2
    print(f"  ✅ 리스트 응답: {len(list_resp.data)}개 항목")

    # 테스트 1-4: 타임스탬프 자동 생성 확인
    print("  [1-4] 타임스탬프 자동 생성 확인...")
    resp1 = success_response(data={"test": 1})
    timestamp1 = datetime.fromisoformat(resp1.timestamp)
    assert timestamp1 is not None
    print(f"  ✅ 타임스탬프: {resp1.timestamp}")

    print("✅ BaseResponse 모델 테스트 통과!\n")


def test_response_serialization():
    """BaseResponse JSON 직렬화 테스트"""
    print("🧪 Test 2: JSON 직렬화 테스트")
    print("=" * 60)

    # Pydantic 모델을 포함한 복잡한 데이터
    messages = [
        MessageResponse(
            user_id="user_1",
            content="쿠폰 발급",
            campaign_name="VIP"
        ),
        MessageResponse(
            user_id="user_2",
            content="포인트 적립",
            campaign_name="Login Bonus"
        )
    ]

    resp = success_response(
        data=[msg.model_dump() for msg in messages],
        message="메시지 생성 완료"
    )

    # JSON 직렬화 테스트
    json_str = resp.model_dump_json()
    assert json_str is not None
    assert "success" in json_str
    assert "user_1" in json_str

    print(f"  ✅ JSON 직렬화 성공 (길이: {len(json_str)} bytes)")
    print(f"  📄 샘플:\n{resp.model_dump_json(indent=2)[:200]}...")
    print("✅ JSON 직렬화 테스트 통과!\n")


def test_response_format_examples():
    """실무 사용 예제 테스트"""
    print("🧪 Test 3: 실무 사용 예제")
    print("=" * 60)

    # 예제 1: 단일 객체 응답
    print("  [예제 1] 캠페인 생성 응답...")
    campaign_resp = success_response(
        data={
            "id": "camp_123",
            "name": "VIP Promotion",
            "status": "active"
        },
        message="캠페인이 생성되었습니다"
    )
    print(f"  ✅ {campaign_resp.message}")

    # 예제 2: 빈 데이터 응답
    print("  [예제 2] 빈 결과 응답...")
    empty_resp = success_response(
        data=[],
        message="조건에 맞는 캠페인이 없습니다"
    )
    assert empty_resp.data == []
    print(f"  ✅ {empty_resp.message}")

    # 예제 3: 에러 응답 (DB 실패)
    print("  [예제 3] DB 에러 응답...")
    db_error = error_response(
        error_code="DB_QUERY_ERROR",
        error_message="데이터베이스 쿼리 실행 실패",
        details={"operation": "insert", "collection": "campaigns"},
        message="캠페인 생성 실패"
    )
    assert db_error.success is False
    print(f"  ✅ 에러 코드: {db_error.error['code']}")

    print("✅ 실무 사용 예제 테스트 통과!\n")


def test_health_check_notes():
    """헬스체크 API 테스트 안내"""
    print("🧪 Test 4: 헬스체크 API (수동 테스트 필요)")
    print("=" * 60)
    print("""
  헬스체크 엔드포인트는 실제 서버를 실행해야 테스트할 수 있습니다.

  📝 테스트 방법:
  1. MongoDB 실행:
     docker-compose up -d mongo

  2. 서버 실행:
     uvicorn app.main:app --reload

  3. 헬스체크 호출:
     curl http://localhost:8000/

  ✅ 예상 응답 (DB 정상):
  {
    "success": true,
    "data": {
      "service": "Clean CRM Engine",
      "version": "1.0.0",
      "status": "healthy",
      "database": "connected"
    },
    "error": null,
    "message": "모든 시스템 정상 작동 중",
    "timestamp": "2026-02-02T..."
  }

  ❌ 예상 응답 (DB 실패, HTTP 503):
  {
    "success": false,
    "data": null,
    "error": {
      "code": "DB_CONNECTION_FAILED",
      "message": "데이터베이스 연결 실패",
      "details": "..."
    },
    "message": "서비스 일시 중지",
    "timestamp": "2026-02-02T..."
  }
    """)
    print("✅ 헬스체크 테스트 안내 완료!\n")


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("🚀 Phase 2 작업 검증 시작")
    print("=" * 60 + "\n")

    test_base_response_model()
    test_response_serialization()
    test_response_format_examples()
    test_health_check_notes()

    print("=" * 60)
    print("✅ Phase 2 테스트 완료!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
