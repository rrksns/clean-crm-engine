# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

사용자의 장바구니 이탈 등 특정 **이벤트(Event)**를 감지하여, 조건에 맞는 타겟에게 자동으로 **쿠폰/메시지(Action)**를 발행하는 DDD 기반의 FastAPI 서비스입니다.

**핵심 특징:**
- ✅ Clean Architecture + DDD 패턴
- ✅ 배치 처리를 통한 고성능 이벤트 처리 (10~20배 성능 향상)
- ✅ 계층별 에러 핸들링 시스템
- ✅ 의존성 주입(DI) 패턴
- ✅ MongoDB 비동기 처리

## 아키텍처 원칙

### Clean Architecture 계층 구조

```
app/
├── domain/           # 핵심 비즈니스 로직 (외부 의존성 0%)
│   ├── models.py     # 엔티티: UserEvent, Campaign, CrmMessage
│   └── services.py   # 도메인 서비스: CampaignMatcher
│
├── application/      # 유즈케이스 계층
│   ├── interfaces.py      # Repository 인터페이스 정의
│   ├── dtos.py            # 입출력 DTO
│   └── event_processor.py # 핵심 비즈니스 로직 (단건/배치 처리)
│
├── infrastructure/   # 외부 연동 계층
│   └── db/
│       ├── models.py       # MongoDB Document 모델
│       ├── repositories.py # Repository 구현체
│       └── connection.py   # DB 연결 설정
│
├── interface/        # API 계층 (Presentation)
│   └── api/
│       └── routes.py       # FastAPI 라우터
│
└── core/             # 공통 인프라
    ├── config.py           # 환경 설정
    └── exceptions.py       # 커스텀 예외 클래스
```

### Domain-Driven Design (DDD)
이 프로젝트는 DDD 원칙을 따릅니다:
- **도메인 엔티티 (`app/domain/models.py`)**: 순수한 비즈니스 객체 (UserEvent, Campaign, CrmMessage)
- **도메인 서비스 (`app/domain/services.py`)**: 비즈니스 로직 구현 (CampaignMatcher)
- **의존성 역전**: 도메인 계층은 외부 의존성(DB, Framework 등)이 없어야 합니다

### 핵심 개념
- **UserEvent**: 사용자 행동 이벤트 (로그인, 상품 조회, 장바구니 추가, 구매 등)
- **Campaign**: 마케팅 규칙 (특정 이벤트 발생 시 조건에 따라 메시지 발송)
- **CampaignMatcher**: 이벤트가 캠페인 조건에 부합하는지 판단하는 도메인 서비스
- **CrmMessage**: 캠페인 조건 충족 시 생성되는 결과 메시지
- **EventProcessor**: 이벤트 처리 유즈케이스 (단건/배치)

## 개발 환경 설정

### 가상환경 활성화
```bash
source venv/bin/activate
```

### 의존성 설치
```bash
pip install -r requirements.txt
```

## 서버 실행

### 개발 모드 (로컬)
```bash
# MongoDB가 실행 중이어야 합니다
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Compose로 실행
```bash
# 앱 + MongoDB 함께 실행
docker-compose up --build
```

### API 문서 확인
```
http://localhost:8000/docs  (Swagger UI)
```

## 테스트

### 전체 테스트 실행
```bash
./venv/bin/pytest
```

### 특정 테스트 파일 실행
```bash
# 도메인 로직 테스트
./venv/bin/pytest tests/test_domain.py

# Phase 1 검증 테스트 (배치 처리 + 에러 핸들링)
python test_phase1.py

# Day 2 테스트 (DB 연결)
python test_day2.py

# Day 3 테스트 (Application 계층)
python test_day3.py
```

### 단일 테스트 함수 실행
```bash
./venv/bin/pytest tests/test_domain.py::test_campaign_matching_logic
```

### Verbose 모드로 실행
```bash
./venv/bin/pytest -v
```

### 커버리지 확인 (선택사항)
```bash
pip install pytest-cov
pytest --cov=app tests/
```

## 성능 최적화 전략

### 배치 처리 (Batch Processing)
대용량 이벤트를 효율적으로 처리하기 위해 배치 API를 제공합니다:

```python
# 단건 처리: POST /api/v1/events
# - DB 조회: 요청마다 1회
# - 100개 요청 = 100회 DB 조회

# 배치 처리: POST /api/v1/events/batch
# - DB 조회: 1회만 수행 (캠페인 목록을 메모리에 캐싱)
# - 100개 요청 = 1회 DB 조회
# - 성능 향상: 약 10~20배 (실제 DB 환경 기준)
```

**구현 위치:**
- `app/application/event_processor.py::process_event_batch()`
- `app/interface/api/routes.py::track_event_batch()`

### 최적화 기법
1. **캠페인 캐싱**: 활성 캠페인을 한 번만 조회하여 메모리에서 재사용
2. **배치 삽입**: `Repository.add_all()` - 여러 레코드를 한 번에 저장
3. **비동기 처리**: Motor 드라이버로 non-blocking I/O 수행

## 에러 핸들링 시스템

### 커스텀 예외 계층 구조

```python
# app/core/exceptions.py

CRMEngineException (기본 예외)
├── DatabaseException
│   ├── DatabaseConnectionException
│   └── DatabaseQueryException
├── ValidationException
├── ResourceNotFoundException
├── DuplicateResourceException
└── ExternalServiceException
```

### 에러 처리 플로우

```
1. Repository 계층
   ↓ PyMongoError 발생
   ↓ DatabaseQueryException으로 변환 (raise ... from e)

2. API 계층 (routes.py)
   ↓ try-except로 캐치
   ↓ 적절한 HTTP 상태 코드로 변환

3. 전역 핸들러 (main.py)
   ↓ 누락된 예외 최후 처리
   ↓ 로깅 및 표준 응답 반환
```

### HTTP 상태 코드 매핑

| 예외 타입 | HTTP 코드 | 설명 |
|---------|---------|------|
| `ValidationException` | 400 | 잘못된 요청 데이터 |
| `ResourceNotFoundException` | 404 | 리소스를 찾을 수 없음 |
| `DuplicateResourceException` | 409 | 중복된 리소스 |
| `DatabaseException` | 500 | 데이터베이스 처리 오류 |
| `DatabaseConnectionException` | 503 | 서비스 이용 불가 |

### 에러 응답 형식

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "'requests' 필드 검증 실패: 최소 1개 이상의 이벤트가 필요합니다",
  "details": {
    "field": "requests",
    "reason": "최소 1개 이상의 이벤트가 필요합니다"
  }
}
```

## API 엔드포인트

### 1. 헬스체크
```http
GET /
```
서버 상태 확인 (DB 연결 상태는 체크하지 않음)

### 2. 이벤트 수신 (단건)
```http
POST /api/v1/events
Content-Type: application/json

{
  "user_id": "user_123",
  "event_type": "add_to_cart",
  "metadata": {
    "price": 60000,
    "product_id": "prod_456"
  }
}
```

**응답:**
```json
[
  {
    "user_id": "user_123",
    "content": "🎁 5천원 할인 쿠폰이 도착했습니다!",
    "campaign_name": "VIP Promotion"
  }
]
```

### 3. 이벤트 배치 처리 (고성능)
```http
POST /api/v1/events/batch
Content-Type: application/json

[
  {
    "user_id": "user_1",
    "event_type": "add_to_cart",
    "metadata": {"price": 70000}
  },
  {
    "user_id": "user_2",
    "event_type": "login",
    "metadata": {}
  }
]
```

### 4. 캠페인 생성
```http
POST /api/v1/campaigns
Content-Type: application/json

{
  "name": "VIP Cart Promotion",
  "target_event": "add_to_cart",
  "min_cart_value": 50000,
  "message_template": "🎁 5천원 할인 쿠폰!"
}
```

## 기술 스택

- **FastAPI**: 웹 프레임워크
- **Pydantic**: 데이터 검증 및 모델링
- **Motor**: MongoDB 비동기 드라이버
- **Beanie**: MongoDB ODM
- **pymongo**: MongoDB 동기 드라이버 (예외 처리용)
- **pytest**: 테스트 프레임워크
- **Python Logging**: 로깅 시스템

## 코드 작성 가이드

### 도메인 모델 추가 시
1. `app/domain/models.py`에 Pydantic BaseModel로 정의
2. 비즈니스 로직은 `app/domain/services.py`에 추가
3. **중요**: 외부 의존성(DB, API 호출 등)을 도메인 계층에 포함하지 않음
4. Enum으로 상수 관리 (EventType, CampaignStatus 등)

### Repository 패턴 구현 시
1. `app/application/interfaces.py`에 인터페이스 정의
2. `app/infrastructure/db/repositories.py`에 구현체 작성
3. **에러 처리 필수**: 모든 DB 작업에 try-except 추가
4. PyMongoError를 커스텀 예외로 변환 (`raise ... from e`)

```python
# 예시
async def add(self, campaign: Campaign) -> Campaign:
    try:
        # DB 작업
        await doc.insert()
        return campaign
    except PyMongoError as e:
        raise DatabaseQueryException(
            operation="insert",
            details=str(e)
        ) from e
```

### API 엔드포인트 추가 시
1. `app/interface/api/routes.py`에 라우터 정의
2. **에러 핸들링 필수**: try-except로 예외 처리
3. 적절한 HTTP 상태 코드 반환
4. 로깅 추가 (`logger.info`, `logger.error` 등)

```python
# 예시
@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
async def create_campaign(...):
    try:
        # 비즈니스 로직
        saved = await repo.add(campaign)
        logger.info(f"Campaign created: {saved.id}")
        return {"id": saved.id}

    except DatabaseException as e:
        logger.error(f"DB error: {e.message}", exc_info=True)
        raise HTTPException(status_code=500, detail=...)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=...)
```

### 테스트 작성 시
- **Given-When-Then 패턴** 사용
- 도메인 로직은 순수 함수처럼 테스트 (외부 의존성 없이)
- 테스트 파일은 `tests/` 디렉토리에 `test_*.py` 형식으로 생성
- Repository는 FakeRepository로 대체하여 테스트

```python
# 예시: test_phase1.py 참고
class FakeCampaignRepository(CampaignRepository):
    def __init__(self):
        self.store = []

    async def add(self, campaign: Campaign) -> Campaign:
        self.store.append(campaign)
        return campaign
```

### 에러 처리 가이드

#### 1. Repository 계층
- **반드시** PyMongoError를 커스텀 예외로 변환
- 에러 체이닝 사용 (`raise ... from e`)

#### 2. API 계층
- 각 엔드포인트에 try-except 추가
- 예외 타입별로 적절한 HTTP 코드 반환
- 로깅 필수

#### 3. 전역 핸들러
- `app/main.py`에 이미 구현됨
- 누락된 예외는 자동으로 처리됨

### 로깅 사용법

```python
import logging

logger = logging.getLogger(__name__)

# 정보성 로그
logger.info(f"Campaign created: {campaign_id}")

# 경고 (예상된 에러)
logger.warning(f"Validation failed: {error}")

# 에러 (복구 가능)
logger.error(f"DB error: {error}", exc_info=True)

# 치명적 에러 (서비스 중단 수준)
logger.critical(f"System failure: {error}", exc_info=True)
```

### Enum 사용
- EventType, CampaignStatus 등 상수는 Enum으로 정의되어 있음
- 새로운 이벤트 타입 추가 시 EventType Enum에 추가

```python
class EventType(str, Enum):
    LOGIN = "login"
    VIEW_PRODUCT = "view_product"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    # 새로운 타입 추가 시 여기에 추가
```

## 주요 파일 구조

### 핵심 비즈니스 로직
- `app/domain/models.py` - 도메인 엔티티 정의
- `app/domain/services.py` - CampaignMatcher (비즈니스 규칙)
- `app/application/event_processor.py` - 이벤트 처리 유즈케이스

### 인프라 계층
- `app/infrastructure/db/repositories.py` - MongoDB Repository 구현
- `app/infrastructure/db/models.py` - Beanie Document 모델
- `app/infrastructure/db/connection.py` - DB 연결 설정

### API 계층
- `app/main.py` - FastAPI 애플리케이션 진입점
- `app/interface/api/routes.py` - API 엔드포인트 정의
- `app/dependencies.py` - 의존성 주입 설정

### 공통
- `app/core/config.py` - 환경 설정
- `app/core/exceptions.py` - 커스텀 예외 클래스
- `app/application/dtos.py` - DTO 정의
- `app/application/interfaces.py` - Repository 인터페이스

### 테스트
- `tests/test_domain.py` - 도메인 로직 단위 테스트
- `test_day2.py` - DB 연결 테스트
- `test_day3.py` - Application 계층 테스트
- `test_phase1.py` - 배치 처리 & 에러 핸들링 검증

## 개발 워크플로우

### 1. 새로운 이벤트 타입 추가
```python
# 1. Enum에 추가
class EventType(str, Enum):
    # ...
    NEW_EVENT = "new_event"

# 2. 캠페인 생성 시 사용 가능
campaign = Campaign(
    target_event=EventType.NEW_EVENT,
    ...
)
```

### 2. 새로운 캠페인 조건 추가
```python
# app/domain/services.py
class CampaignMatcher:
    @staticmethod
    def is_match(campaign: Campaign, event: UserEvent) -> bool:
        # 기존 조건들...

        # 새로운 조건 추가
        if campaign.some_new_field:
            # 새로운 비즈니스 로직
            pass

        return True
```

### 3. 새로운 Repository 메서드 추가
```python
# 1. 인터페이스 정의
class CampaignRepository(ABC):
    @abstractmethod
    async def new_method(self, ...) -> ...:
        pass

# 2. 구현
class MongoCampaignRepository(CampaignRepository):
    async def new_method(self, ...) -> ...:
        try:
            # DB 작업
            pass
        except PyMongoError as e:
            raise DatabaseQueryException(...) from e
```

### 4. 새로운 API 엔드포인트 추가
```python
# app/interface/api/routes.py
@router.post("/new-endpoint")
async def new_endpoint(...):
    try:
        # 비즈니스 로직
        logger.info("...")
        return {...}
    except DatabaseException as e:
        logger.error(f"...", exc_info=True)
        raise HTTPException(...)
```

## 트러블슈팅

### MongoDB 연결 실패
```bash
# MongoDB가 실행 중인지 확인
docker ps | grep mongo

# Docker Compose로 MongoDB 실행
docker-compose up -d mongo
```

### 테스트 실패 시
```bash
# 가상환경 활성화 확인
source venv/bin/activate

# 의존성 재설치
pip install -r requirements.txt

# pytest 재설치
pip install pytest
```

### Import 에러 발생 시
```bash
# PYTHONPATH 설정 (프로젝트 루트에서 실행)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 또는 pytest 사용
pytest tests/test_domain.py
```

## 성능 테스트

### 스트레스 테스트 실행
```bash
# MongoDB 실행 후
python scripts/stress_test.py
```

예상 결과:
- 단건 처리: ~10초 (100개 이벤트)
- 배치 처리: ~0.5초 (100개 이벤트)
- 성능 향상: **약 20배**

## Python 버전
- Python 3.9.6 이상 권장

## 참고 자료
- Clean Architecture: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- Beanie ODM: https://beanie-odm.dev/
