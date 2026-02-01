# app/core/exceptions.py
"""
커스텀 예외 클래스 정의

실무에서는 도메인별로 예외를 구분하여 관리합니다.
이를 통해 에러 발생 지점을 명확히 추적하고, 적절한 HTTP 상태 코드로 변환할 수 있습니다.
"""
from typing import Optional, Any


class CRMEngineException(Exception):
    """
    모든 커스텀 예외의 기본 클래스

    이 클래스를 상속받아 도메인별 예외를 정의합니다.
    """
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Any] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details
        super().__init__(self.message)


# ─────────────────────────────────────────────────
# 데이터베이스 관련 예외
# ─────────────────────────────────────────────────

class DatabaseException(CRMEngineException):
    """데이터베이스 작업 중 발생하는 예외"""
    pass


class DatabaseConnectionException(DatabaseException):
    """DB 연결 실패"""
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="데이터베이스 연결에 실패했습니다",
            code="DB_CONNECTION_ERROR",
            details=details
        )


class DatabaseQueryException(DatabaseException):
    """DB 쿼리 실행 실패"""
    def __init__(self, operation: str, details: Optional[Any] = None):
        super().__init__(
            message=f"데이터베이스 {operation} 작업에 실패했습니다",
            code="DB_QUERY_ERROR",
            details=details
        )


# ─────────────────────────────────────────────────
# 비즈니스 로직 관련 예외
# ─────────────────────────────────────────────────

class ValidationException(CRMEngineException):
    """데이터 검증 실패"""
    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"'{field}' 필드 검증 실패: {reason}",
            code="VALIDATION_ERROR",
            details={"field": field, "reason": reason}
        )


class ResourceNotFoundException(CRMEngineException):
    """리소스를 찾을 수 없음"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type}(ID: {resource_id})을(를) 찾을 수 없습니다",
            code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "id": resource_id}
        )


class DuplicateResourceException(CRMEngineException):
    """중복된 리소스"""
    def __init__(self, resource_type: str, field: str, value: str):
        super().__init__(
            message=f"이미 존재하는 {resource_type}입니다 ({field}: {value})",
            code="DUPLICATE_RESOURCE",
            details={"resource_type": resource_type, "field": field, "value": value}
        )


# ─────────────────────────────────────────────────
# 외부 서비스 관련 예외
# ─────────────────────────────────────────────────

class ExternalServiceException(CRMEngineException):
    """외부 서비스 호출 실패 (향후 확장용)"""
    def __init__(self, service_name: str, details: Optional[Any] = None):
        super().__init__(
            message=f"{service_name} 서비스 호출에 실패했습니다",
            code="EXTERNAL_SERVICE_ERROR",
            details=details
        )
