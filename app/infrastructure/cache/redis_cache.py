# app/infrastructure/cache/redis_cache.py
import logging
from typing import Optional
import redis.asyncio as aioredis
from app.application.interfaces import CacheService
from app.core.config import settings

logger = logging.getLogger(__name__)

# 전역 Redis 클라이언트 (싱글톤 패턴)
_redis_client: Optional[aioredis.Redis] = None


async def connect_to_redis() -> None:
    """
    Redis 서버에 연결합니다.
    앱 시작 시 lifespan에서 호출됩니다.
    """
    global _redis_client
    try:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        # 연결 확인
        await _redis_client.ping()
        logger.info(f"✅ Redis 연결 성공: {settings.REDIS_URL}")
    except Exception as e:
        logger.error(f"❌ Redis 연결 실패: {e}", exc_info=True)
        _redis_client = None
        raise


async def close_redis() -> None:
    """
    Redis 연결을 종료합니다.
    앱 종료 시 lifespan에서 호출됩니다.
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis 연결 종료")
        _redis_client = None


def get_redis_client() -> Optional[aioredis.Redis]:
    """
    현재 Redis 클라이언트를 반환합니다.
    """
    return _redis_client


class RedisCacheService(CacheService):
    """
    Redis 기반 캐시 서비스 구현체.

    특징:
    - Graceful degradation: Redis 장애 시 조용히 실패 (캐시 없이 DB 사용)
    - 모든 메서드는 try-except로 감싸져 있어 캐시 실패가 전체 시스템에 영향 없음
    """

    async def get(self, key: str) -> Optional[str]:
        """
        캐시에서 값을 조회합니다.

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None (캐시 미스 또는 Redis 장애)
        """
        client = get_redis_client()
        if client is None:
            logger.debug("Redis 클라이언트가 없습니다 (캐시 미스 처리)")
            return None

        try:
            value = await client.get(key)
            if value:
                logger.debug(f"캐시 히트: {key}")
            return value
        except Exception as e:
            logger.warning(f"캐시 조회 실패 (키: {key}): {e}")
            return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        """
        캐시에 값을 저장합니다.

        Args:
            key: 캐시 키
            value: 저장할 값 (JSON 문자열)
            ttl: 만료 시간 (초)
        """
        client = get_redis_client()
        if client is None:
            logger.debug("Redis 클라이언트가 없습니다 (캐시 저장 건너뜀)")
            return

        try:
            await client.setex(key, ttl, value)
            logger.debug(f"캐시 저장: {key} (TTL: {ttl}초)")
        except Exception as e:
            logger.warning(f"캐시 저장 실패 (키: {key}): {e}")

    async def delete(self, key: str) -> None:
        """
        캐시에서 키를 삭제합니다 (무효화).

        Args:
            key: 삭제할 캐시 키
        """
        client = get_redis_client()
        if client is None:
            logger.debug("Redis 클라이언트가 없습니다 (캐시 무효화 건너뜀)")
            return

        try:
            await client.delete(key)
            logger.debug(f"캐시 무효화: {key}")
        except Exception as e:
            logger.warning(f"캐시 무효화 실패 (키: {key}): {e}")
