# clean-crm-engine
"사용자의 장바구니 이탈 등 특정 **이벤트(Event)**를 감지하여, 조건에 맞는 타겟에게 자동으로 **쿠폰/메시지(Action)**를 발행하는 DDD 기반의 FastAPI 서비스"

# Clean CRM Engine (Marketing Automation API)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-Motor%20%26%20Beanie-47A248?logo=mongodb)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Architecture](https://img.shields.io/badge/Architecture-Clean%20%26%20DDD-orange)

## 📖 프로젝트 소개
**"데이터가 성장을 만든다(Data Makes Growth)"**
이 프로젝트는 이커머스 고객의 행동 데이터(Event)를 실시간으로 분석하여, 맞춤형 마케팅 메시지(Action)를 자동 발행하는 **CRM 자동화 엔진**입니다.

대용량 트래픽 처리가 필수적인 마케팅 솔루션의 특성을 고려하여 **비동기(Async) 기반의 FastAPI**와 **NoSQL(MongoDB)**을 채택했으며, 비즈니스 로직의 유연한 확장을 위해 **Clean Architecture**를 적용했습니다.

### 🎯 핵심 기능
* **실시간 이벤트 감지:** 장바구니 담기, 상품 조회 등 사용자 행동 수집.
* **타겟팅 룰 엔진:** 마케터가 설정한 조건(예: 5무만원 이상 장바구니 & 미구매) 매칭 로직.
* **고성능 배치 처리:** 대량의 이벤트를 한 번에 처리하는 `Batch API` 구현 (단건 대비 **20배 성능 향상**).
* **Redis 캐싱:** 활성 캠페인 조회에 Cache-Aside 패턴 적용, 반복 조회 성능 대폭 향상 (TTL 5분).
* **DB 인덱스 최적화:** 10개 인덱스로 쿼리 성능 O(log n) 개선, COLLSCAN → IXSCAN 전환.
* **계층별 에러 핸들링:** Repository → API → 전역 핸들러 3단계 방어선, 7가지 커스텀 예외 클래스.
* **API 버전 관리:** v2 API 추가 (BaseResponse 표준 형식), v1은 하위 호환성 유지 (deprecated).
* **헬스체크 강화:** MongoDB 연결 상태 실시간 확인, K8s liveness/readiness probe 지원.
* **Docker 기반 배포:** 개발 및 운영 환경의 일치성을 보장하는 컨테이너 환경 구축.

---

## 🏗 아키텍처 (Clean Architecture)
Spring 개발 경험을 바탕으로, Python 환경에서도 **관심사의 분리(Separation of Concerns)**를 명확히 했습니다.

```text
app/
├── domain/         # [Core] 순수 비즈니스 로직 (Campaign, Event, Rule) - 외부 라이브러리 의존성 0%
├── application/    # [Use Case] 서비스 계층 (Processor) - Repository 인터페이스에 의존
├── infrastructure/ # [Adapter] DB 구현체 (MongoDB/Beanie), 외부 API 연동
├── interface/      # [Presentation] Web API (FastAPI Router), DTO 정의
└── core/           # [Common] 공통 인프라 (예외, 설정, 로깅)
```

**의존성 흐름:**
```
Presentation → Application → Domain ← Infrastructure
                                ↑
                              Core
```

---

## ⚡ 성능 최적화

### 배치 처리 (Batch Processing)
대량 트래픽 처리를 위한 핵심 최적화 기법입니다.

```python
# 단건 처리 API: POST /api/v1/events
# - 100개 요청 = 100회 DB 조회
# - 처리 시간: ~10초

# 배치 처리 API: POST /api/v1/events/batch
# - 100개 요청 = 1회 DB 조회 (메모리 캐싱)
# - 처리 시간: ~0.5초
# - 성능 향상: 약 20배 ⚡
```

**최적화 기법:**
1. **캠페인 캐싱**: 활성 캠페인을 한 번만 조회하여 메모리에서 재사용
2. **배치 삽입**: `Repository.add_all()` - 여러 레코드를 한 번에 저장
3. **비동기 처리**: Motor 드라이버로 non-blocking I/O 수행

### Redis 캐싱 (Cache-Aside 패턴)
반복되는 활성 캠페인 조회를 최적화하여 DB 부하를 감소시킵니다.

```python
# get_active_campaigns() 호출 흐름:
# 1. Redis 캐시 확인 → 히트 시 즉시 반환 (DB 조회 생략)
# 2. 캐시 미스 → MongoDB 조회
# 3. 조회 결과를 Redis에 저장 (TTL: 5분)
# 4. 결과 반환

# 캠페인 추가/수정 시:
# - add() / add_all() 성공 후 자동으로 캐시 무효화
# - 다음 조회 시 최신 데이터로 캐시 재생성
```

**Graceful Degradation:**
- Redis 다운 시 자동으로 MongoDB로 폴백
- 캐시 장애가 전체 시스템에 영향을 주지 않음
- 앱 시작 시 Redis 연결 실패해도 정상 동작

---

## 🛡️ 에러 핸들링 시스템

### 3계층 방어선
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

### 커스텀 예외 계층 구조
```python
CRMEngineException (기본 예외)
├── DatabaseException
│   ├── DatabaseConnectionException  # 503 Service Unavailable
│   └── DatabaseQueryException       # 500 Internal Server Error
├── ValidationException              # 400 Bad Request
├── ResourceNotFoundException        # 404 Not Found
├── DuplicateResourceException       # 409 Conflict
└── ExternalServiceException         # 502 Bad Gateway
```

---

## 📡 API 엔드포인트

### API 버전 관리
- **v1**: `/api/v1/*` - 기존 형식 (deprecated, 하위 호환성 유지)
- **v2**: `/api/v2/*` - BaseResponse 표준 형식 (권장) ⭐

### 1. API 정보 (루트)
```http
GET /
```
**응답:**
```json
{
  "service": "Clean CRM Engine",
  "description": "이벤트 기반 마케팅 자동화 API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": {
    "liveness": "/health/live",
    "readiness": "/health/ready"
  },
  "api": {
    "v1": "/api/v1 (deprecated)",
    "v2": "/api/v2 (recommended)"
  }
}
```

### 2. 헬스체크 (Kubernetes 스타일)

#### Liveness Probe (앱 살아있는지 확인)
```http
GET /health/live
```
**용도**: Kubernetes liveness probe, 앱 크래시 감지
**응답**: 항상 200 OK (외부 의존성 체크 없음)
```json
{
  "status": "alive"
}
```

#### Readiness Probe (트래픽 수신 준비 확인)
```http
GET /health/ready
```
**용도**: Kubernetes readiness probe, 트래픽 수신 가능 여부
**응답**: DB 연결 포함 상태 체크
```json
{
  "success": true,
  "data": {
    "service": "Clean CRM Engine",
    "version": "1.0.0",
    "status": "ready",
    "database": "connected"
  },
  "message": "트래픽 수신 준비 완료",
  "timestamp": "2026-02-10T00:54:03"
}
```

### 3. 이벤트 수신 (단건)
```http
POST /api/v2/events  (권장)
POST /api/v1/events  (deprecated)
```
**요청:**
```json
{
  "user_id": "user_123",
  "event_type": "add_to_cart",
  "metadata": {"price": 60000, "product_id": "prod_456"}
}
```

**v2 응답 (BaseResponse):**
```json
{
  "success": true,
  "data": [
    {
      "user_id": "user_123",
      "content": "🎁 5천원 할인 쿠폰!",
      "campaign_name": "VIP Cart Promotion"
    }
  ],
  "message": "이벤트 처리 완료 (1개 메시지 생성)",
  "timestamp": "2026-02-09T10:30:00"
}
```

### 4. 이벤트 배치 처리 (고성능) ⚡
```http
POST /api/v2/events/batch  (권장)
POST /api/v1/events/batch  (deprecated)
```
**요청:**
```json
[
  {"user_id": "user_1", "event_type": "add_to_cart", "metadata": {"price": 70000}},
  {"user_id": "user_2", "event_type": "login", "metadata": {}}
]
```

### 5. 캠페인 생성
```http
POST /api/v2/campaigns  (권장)
POST /api/v1/campaigns  (deprecated)
```
**요청:**
```json
{
  "name": "VIP Cart Promotion",
  "target_event": "add_to_cart",
  "min_cart_value": 50000,
  "message_template": "🎁 5천원 할인 쿠폰!"
}
```

### 6. 캠페인 목록 조회 (페이지네이션)
```http
GET /api/v2/campaigns?cursor=<cursor>&limit=20&status=active
```

---

## 🚀 빠른 시작

### 1. Docker Compose로 실행 (권장)
```bash
# MongoDB + Redis + 애플리케이션 실행
docker-compose up --build

# API 문서 확인
open http://localhost:8000/docs
```

### 2. 로컬 개발 환경
```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. MongoDB + Redis 실행 (Docker)
docker-compose up -d mongodb redis

# 4. 서버 실행
uvicorn app.main:app --reload

# 5. API 문서 확인
open http://localhost:8000/docs
```

---

## 🧪 테스트

```bash
# 전체 테스트 실행 (42개)
PYTHONPATH=. pytest tests/ -v

# API v1 테스트 (19개)
PYTHONPATH=. pytest tests/test_api.py -v

# API v2 테스트 (6개)
PYTHONPATH=. pytest tests/test_api_v2.py -v

# 헬스체크 테스트 (8개)
PYTHONPATH=. pytest tests/test_health.py -v

# 캐시 테스트 (5개)
PYTHONPATH=. pytest tests/test_cache.py -v

# 인덱스 테스트 (3개)
PYTHONPATH=. pytest tests/test_indexes.py -v

# 도메인 로직 테스트 (1개)
PYTHONPATH=. pytest tests/test_domain.py -v
```

---

## 📚 문서

- **[CLAUDE.md](CLAUDE.md)**: 프로젝트 가이드 (아키텍처, 코드 작성 가이드, 워크플로우)
- **[PROGRESS.md](PROGRESS.md)**: 진행 상황 및 로드맵
- **[API 문서](http://localhost:8000/docs)**: Swagger UI (서버 실행 후)

---

## 🎯 주요 성과

| 항목 | 성과 |
|-----|------|
| **성능** | 배치 처리로 **20배 향상** (100개 이벤트: 10초 → 0.5초) |
| **캐싱** | Redis Cache-Aside 패턴 적용, 반복 조회 성능 향상 |
| **인덱스** | 10개 인덱스로 쿼리 성능 O(log n) 개선, COLLSCAN → IXSCAN |
| **아키텍처** | Clean Architecture + DDD 적용 |
| **API 버전 관리** | v2 API 추가 (BaseResponse), v1 하위 호환 유지 |
| **에러 처리** | 3계층 방어선 (Repository → API → 전역) |
| **테스트** | 42개 테스트 통과 (API v1 19, v2 6, 헬스체크 8, 캐시 5, 인덱스 3, 도메인 1) |
| **운영 준비** | 헬스체크, 로깅, 표준화된 API 응답, graceful degradation |
| **문서화** | CLAUDE.md, README.md, PROGRESS.md 지속 업데이트 |

---

## 🛠️ 기술 스택

**Backend:**
- FastAPI 0.100+ (비동기 웹 프레임워크)
- Pydantic 2.0+ (데이터 검증 및 직렬화)

**Database:**
- MongoDB 5.0+ (NoSQL 데이터베이스)
- Motor (비동기 MongoDB 드라이버)
- Beanie 1.20+ (MongoDB ODM)

**Cache:**
- Redis 7.x (인메모리 캐시)
- redis-py 7.0+ (비동기 Redis 클라이언트)

**Infrastructure:**
- Docker & Docker Compose (컨테이너화)
- Python 3.9.6+ (런타임)

**Development:**
- pytest (테스트 프레임워크)
- Python logging (로깅 시스템)

---

## 📄 라이선스

이 프로젝트는 학습 및 포트폴리오 목적으로 제작되었습니다.

---

## 👤 제작자

**작업 기간**: 2025-01-05 ~ 2026-02-02
**주요 기술**: Clean Architecture, DDD, FastAPI, MongoDB, Docker

---

**마지막 업데이트**: 2026-02-10
**다음 계획**: Rate Limiting 구현, 인증/인가 시스템
