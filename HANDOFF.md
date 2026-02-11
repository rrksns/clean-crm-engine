# HANDOFF.md
> 컨텍스트 유실 방지용 인수인계 문서
> 마지막 업데이트: 2026-02-11

---

## 현재 개발 상태

### 완료된 Phase
| Phase | 내용 | 커밋 |
|-------|------|------|
| Phase 1 | 배치 처리 & 에러 핸들링 | `b386587` |
| Phase 2 | API 응답 표준화, 헬스체크, 이벤트 저장 | `83e7aaf` |
| Phase 3-1 | 캠페인 목록 커서 기반 페이지네이션 | `b44d461` |
| Phase 3-2 | Redis 캐싱 레이어 | `c6a2324` |
| Phase 3-3 | 데이터베이스 인덱스 최적화 | `33f9529` |
| API v2 | BaseResponse 표준 형식 | `49cbc11` |해
| 헬스체크 리팩토링 | Kubernetes liveness/readiness probe | `981045c` |

---

## 미결 아이디어: 로그 포맷 전략

### 현재 구현 (`app/main.py:16-18`)
```python
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

현재 포맷 출력 예시:
```
2026-02-11 10:23:45,123 - app.interface.api.routes_v2 - INFO - Campaign created successfully: 64f1a2b3c4d5e6f7
2026-02-11 10:23:45,456 - app.main - WARNING - Redis 연결 실패, 캐시 없이 운영됩니다: ...
```

### 논의된 아이디어: 2단계 로그 포맷 전략

**Phase A (현재) - 터미널 친화적 포맷 유지**
- 개발/운영 초기에는 사람이 직접 읽기 좋은 현재 포맷 유지
- `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- `docker logs`, `kubectl logs` 등으로 바로 읽을 수 있어 편리

**Phase B (추후) - JSON 구조화 로깅으로 전환**
- ELK Stack, Datadog, Grafana Loki 등 로그 관리 솔루션 도입 시점에 전환
- 전환 시 `python-json-logger` 라이브러리 도입 검토

```python
# 추후 전환 시 예상 구현 (app/main.py)
from pythonjsonlogger import jsonlogger

def setup_logging():
    handler = logging.StreamHandler()
    if settings.LOG_FORMAT == "json":
        # 로그 솔루션 연동 시: JSON 포맷
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        # 기본 개발 환경: 터미널 가독성 우선
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    handler.setFormatter(formatter)
    logging.basicConfig(level=..., handlers=[handler])
```

JSON 포맷 출력 예시:
```json
{"asctime": "2026-02-11 10:23:45", "name": "app.routes_v2", "levelname": "INFO", "message": "Campaign created successfully: 64f1a2b3"}
```

**전환 트리거 조건 (판단 기준)**
- 로그를 검색하거나 필터링할 일이 생기면 → JSON 전환 시점
- 서버가 2대 이상으로 늘어나면 → 중앙 집중 로그 솔루션 + JSON 전환
- 에러 알림 자동화가 필요하면 → JSON 전환

### 관련 파일
- `app/main.py:15-20` - 현재 로깅 설정
- `app/core/config.py` - `LOG_LEVEL` 환경변수 (`INFO` 기본값)
- `app/interface/api/routes.py`, `routes_v2.py` - 각 엔드포인트의 logger 사용

---

## 다음 작업 후보 (미결)

아래 항목들은 논의되었으나 아직 구현되지 않은 내용입니다:

- [ ] **로그 포맷 환경변수화**: `LOG_FORMAT=json|text` 설정 추가 (위 Phase B 구현)
- [ ] **구조화 로그 필드 표준화**: `user_id`, `campaign_id`, `event_type` 등을 로그에 일관되게 포함
- [ ] **로그 레벨 재검토**: 현재 routes에서 모든 DB 에러가 `ERROR`인데, 일부는 `WARNING`이 적절할 수 있음

---

## 주요 아키텍처 결정 사항 (ADR)

### ADR-001: 로그 포맷 - 터미널 우선
- **결정**: 현재는 인간 가독성 우선의 텍스트 포맷 유지
- **이유**: 로그 관리 솔루션 미도입 상태에서 JSON은 오버엔지니어링
- **재검토 시점**: 중앙 로그 수집 솔루션 도입 시

### ADR-002: Redis 캐시 선택적 연결
- **결정**: Redis 연결 실패 시 앱이 정상 시작되도록 구현 (`app/main.py:27-30`)
- **이유**: Redis는 선택적 성능 최적화이므로, 미연결 상태에서도 서비스 가용성 보장

### ADR-003: API 버전 관리
- **결정**: v1 deprecated 유지 + v2 신규 권장
- **이유**: 하위 호환성 유지 (기존 클라이언트 영향 없음)
- **v2 특징**: `BaseResponse` 표준 형식 (`success`, `data`, `error`, `message`, `timestamp`)
