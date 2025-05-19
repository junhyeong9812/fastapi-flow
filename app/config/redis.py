"""
✅ Redis 클라이언트 설정
- 세션 관리 및 토큰 저장을 위한 Redis 연결 클래스
- 비동기(async) Redis 클라이언트 사용
- 애플리케이션 시작/종료 시 연결 관리
"""
from typing import Optional
import aioredis
import logging
from pydantic import BaseModel

# 로깅 설정
logger = logging.getLogger(__name__)

class RedisSettings(BaseModel):
    """Redis 연결 설정"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = "redispassword"
    db: int = 0
    encoding: str = "utf-8"
    max_connections: int = 10


class RedisClient:
    """
    Redis 클라이언트 싱글톤 클래스
    - 애플리케이션에서 공유하는 Redis 연결 관리
    - 토큰 저장 및 세션 관리를 위한 유틸리티 메서드 제공
    """
    _instance = None
    _redis: Optional[aioredis.Redis] = None
    
    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    async def initialize(cls, settings: Optional[RedisSettings] = None) -> None:
        """
        Redis 클라이언트 초기화
        - 애플리케이션 시작 시 호출
        """
        if settings is None:
            settings = RedisSettings()
        
        if cls._redis is not None:
            logger.warning("[RedisClient] Redis 클라이언트가 이미 초기화되어 있습니다")
            return
        
        try:
            # Redis 연결 문자열 생성
            redis_url = f"redis://:{settings.password}@{settings.host}:{settings.port}/{settings.db}"
            
            # Redis 연결
            cls._redis = aioredis.from_url(
                redis_url,
                encoding=settings.encoding,
                max_connections=settings.max_connections
            )
            
            # 연결 테스트
            await cls._redis.ping()
            
            logger.info(f"[RedisClient] Redis 연결 성공: {settings.host}:{settings.port}")
        except Exception as e:
            logger.error(f"[RedisClient] Redis 연결 실패: {str(e)}")
            raise
    
    @classmethod
    async def close(cls) -> None:
        """
        Redis 연결 종료
        - 애플리케이션 종료 시 호출
        """
        if cls._redis is not None:
            await cls._redis.close()
            cls._redis = None
            logger.info("[RedisClient] Redis 연결 종료")
    
    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        """
        Redis 클라이언트 반환
        - 초기화되지 않은 경우 자동 초기화
        """
        if cls._redis is None:
            await cls.initialize()
        return cls._redis
    
    @classmethod
    async def set_key(cls, key: str, value: str, expire: int = None) -> bool:
        """
        키-값 저장
        - expire: 만료 시간(초)
        """
        redis = await cls.get_client()
        await redis.set(key, value)
        if expire is not None:
            await redis.expire(key, expire)
        return True
    
    @classmethod
    async def get_key(cls, key: str) -> Optional[str]:
        """키로 값 조회"""
        redis = await cls.get_client()
        return await redis.get(key)
    
    @classmethod
    async def delete_key(cls, key: str) -> bool:
        """키 삭제"""
        redis = await cls.get_client()
        return await redis.delete(key) > 0
    
    @classmethod
    async def set_token(cls, user_id: str, token: str, expire: int = 3600) -> bool:
        """
        사용자 토큰 저장
        - 리프레시 토큰 저장에 사용
        - user_id: 사용자 ID
        - token: 토큰 값
        - expire: 만료 시간(초, 기본 1시간)
        """
        key = f"token:{user_id}"
        return await cls.set_key(key, token, expire)
    
    @classmethod
    async def get_token(cls, user_id: str) -> Optional[str]:
        """사용자 토큰 조회"""
        key = f"token:{user_id}"
        return await cls.get_key(key)
    
    @classmethod
    async def delete_token(cls, user_id: str) -> bool:
        """사용자 토큰 삭제"""
        key = f"token:{user_id}"
        return await cls.delete_key(key)
    
    @classmethod
    async def save_refresh_token(cls, user_id: str, refresh_token: str, expire_days: int = 7) -> bool:
        """
        리프레시 토큰 저장
        - 사용자 ID를 키로 사용
        - expire_days: 만료 일수
        """
        return await cls.set_token(user_id, refresh_token, expire_days * 24 * 3600)
    
    @classmethod
    async def verify_refresh_token(cls, user_id: str, refresh_token: str) -> bool:
        """
        리프레시 토큰 검증
        - 저장된 토큰과 일치하는지 확인
        """
        stored_token = await cls.get_token(user_id)
        return stored_token == refresh_token