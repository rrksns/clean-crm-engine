# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

사용자의 장바구니 이탈 등 특정 **이벤트(Event)**를 감지하여, 조건에 맞는 타겟에게 자동으로 **쿠폰/메시지(Action)**를 발행하는 DDD 기반의 FastAPI 서비스입니다.

## 아키텍처 원칙

### Domain-Driven Design (DDD)
이 프로젝트는 DDD 원칙을 따릅니다:
- **도메인 엔티티 (`app/domain/models.py`)**: 순수한 비즈니스 객체 (UserEvent, Campaign, CrmMessage)
- **도메인 서비스 (`app/domain/services.py`)**: 비즈니스 로직 구현 (CampaignMatcher)
- 도메인 계층은 외부 의존성(DB, Framework 등)이 없어야 합니다

### 핵심 개념
- **UserEvent**: 사용자 행동 이벤트 (로그인, 상품 조회, 장바구니 추가, 구매 등)
- **Campaign**: 마케팅 규칙 (특정 이벤트 발생 시 조건에 따라 메시지 발송)
- **CampaignMatcher**: 이벤트가 캠페인 조건에 부합하는지 판단하는 도메인 서비스
- **CrmMessage**: 캠페인 조건 충족 시 생성되는 결과 메시지

## 개발 환경 설정

### 가상환경 활성화
```bash
source venv/bin/activate
```

### 의존성 설치
```bash
pip install -r requirements.txt
```

## 테스트

### 전체 테스트 실행
```bash
./venv/bin/pytest
```

### 특정 테스트 파일 실행
```bash
./venv/bin/pytest tests/test_domain.py
```

### 단일 테스트 함수 실행
```bash
./venv/bin/pytest tests/test_domain.py::test_campaign_matching_logic
```

### Verbose 모드로 실행
```bash
./venv/bin/pytest -v
```

## 기술 스택

- **FastAPI**: 웹 프레임워크
- **Pydantic**: 데이터 검증 및 모델링
- **Motor**: MongoDB 비동기 드라이버
- **Beanie**: MongoDB ODM
- **pytest**: 테스트 프레임워크

## 코드 작성 가이드

### 도메인 모델 추가 시
1. `app/domain/models.py`에 Pydantic BaseModel로 정의
2. 비즈니스 로직은 `app/domain/services.py`에 추가
3. 외부 의존성(DB, API 호출 등)을 도메인 계층에 포함하지 않음

### 테스트 작성 시
- Given-When-Then 패턴 사용
- 도메인 로직은 순수 함수처럼 테스트 (외부 의존성 없이)
- 테스트 파일은 `tests/` 디렉토리에 `test_*.py` 형식으로 생성

### Enum 사용
- EventType, CampaignStatus 등 상수는 Enum으로 정의되어 있음
- 새로운 이벤트 타입 추가 시 EventType Enum에 추가

## Python 버전
- Python 3.9.6
