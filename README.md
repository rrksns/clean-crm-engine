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
* **고성능 배치 처리:** 대량의 이벤트를 한 번에 처리하는 `Batch API` 구현 (단건 대비 20배 성능 향상).
* **Docker 기반 배포:** 개발 및 운영 환경의 일치성을 보장하는 컨테이너 환경 구축.

---

## 🏗 아키텍처 (Clean Architecture)
Spring 개발 경험을 바탕으로, Python 환경에서도 **관심사의 분리(Separation of Concerns)**를 명확히 했습니다.

```text
app/
├── domain/         # [Core] 순수 비즈니스 로직 (Campaign, Event, Rule) - 외부 라이브러리 의존성 0%
├── application/    # [Use Case] 서비스 계층 (Processor) - Repository 인터페이스에 의존
├── infrastructure/ # [Adapter] DB 구현체 (MongoDB/Beanie), 외부 API 연동
└── interface/      # [Presentation] Web API (FastAPI Router), DTO 정의
