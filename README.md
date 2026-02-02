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
* **타겟팅 룰 엔진:** 마케터가 설정한 조건(예: 5만원 이상 장바구니 & 미구매) 매칭 로직.
* **고성능 배치 처리:** 대량의 이벤트를 한 번에 처리하는 `Batch API` 구현 (단건 대비 **20배 성능 향상**).
* **계층별 에러 핸들링:** Repository → API → 전역 핸들러 3단계 방어선, 7가지 커스텀 예외 클래스.
* **API 응답 표준화:** 성공/에러 응답 일관된 형식 제공 (BaseResponse), 타임스탬프 자동 생성.
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

### 1. 헬스체크
```http
GET /
```
**응답 예시:**
```json
{
  "success": true,
  "data": {
    "service": "Clean CRM Engine",
    "version": "1.0.0",
    "status": "healthy",
    "database": "connected"
  },
  "message": "모든 시스템 정상 작동 중",
  "timestamp": "2026-02-02T10:30:00"
}
```

### 2. 이벤트 수신 (단건)
```http
POST /api/v1/events
```
**요청:**
```json
{
  "user_id": "user_123",
  "event_type": "add_to_cart",
  "metadata": {"price": 60000, "product_id": "prod_456"}
}
```

### 3. 이벤트 배치 처리 (고성능) ⚡
```http
POST /api/v1/events/batch
```
**요청:**
```json
[
  {"user_id": "user_1", "event_type": "add_to_cart", "metadata": {"price": 70000}},
  {"user_id": "user_2", "event_type": "login", "metadata": {}}
]
```

### 4. 캠페인 생성
```http
POST /api/v1/campaigns
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

---

## 🚀 빠른 시작

### 1. Docker Compose로 실행 (권장)
```bash
# MongoDB + 애플리케이션 실행
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

# 3. MongoDB 실행 (Docker)
docker-compose up -d mongo

# 4. 서버 실행
uvicorn app.main:app --reload

# 5. API 문서 확인
open http://localhost:8000/docs
```

---

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# Phase 1 검증 (배치 처리 & 에러 핸들링)
python test_phase1.py

# Phase 2 검증 (API 응답 표준화 & 헬스체크)
python test_phase2.py

# 도메인 로직 테스트
pytest tests/test_domain.py -v
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
| **아키텍처** | Clean Architecture + DDD 적용 |
| **에러 처리** | 3계층 방어선 (Repository → API → 전역) |
| **테스트** | 도메인/Application/Phase 검증 테스트 완료 |
| **운영 준비** | 헬스체크, 로깅, 표준화된 API 응답 |
| **문서화** | 547줄 가이드 문서 (CLAUDE.md) |

---

## 🛠️ 기술 스택

**Backend:**
- FastAPI 0.100+ (비동기 웹 프레임워크)
- Pydantic 2.0+ (데이터 검증 및 직렬화)

**Database:**
- MongoDB 5.0+ (NoSQL 데이터베이스)
- Motor (비동기 MongoDB 드라이버)
- Beanie 1.20+ (MongoDB ODM)

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

**마지막 업데이트**: 2026-02-02
**다음 계획**: 이벤트 저장 기능, 페이지네이션, 캐싱 레이어 구현
