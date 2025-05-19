"""
✅ JWT 토큰 보안 설정
- Spring Security의 JWT 서비스와 유사한 기능 제공
- 토큰 생성, 검증, 정보 추출 등 기능 구현
- Redis를 활용한 토큰 관리
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, Union, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
import logging

from app.config.settings import get_settings
from app.config.redis import RedisClient

# 로깅 설정
logger = logging.getLogger(__name__)

# 설정 가져오기
settings = get_settings()

# 비밀번호 해싱을 위한 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenPayload(BaseModel):
    """토큰 페이로드 모델"""
    sub: str
    role: Optional[str] = None
    exp: Optional[int] = None


class JWTTokenService:
    """
    JWT 토큰 서비스
    - Spring Security의 JwtTokenProvider와 유사한 역할
    - 토큰 생성, 검증, 페이로드 추출 등 기능 제공
    - Redis를 활용한 토큰 관리
    """
    
    @staticmethod
    def create_access_token(
        subject: Union[str, Dict[str, Any]],
        role: Optional[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        액세스 토큰 생성
        - 사용자 ID 및 역할 정보가 포함된 토큰 생성
        """
        to_encode = {}
        
        # 만료 시간 설정
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.security.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # 페이로드 구성
        to_encode.update({"sub": str(subject), "exp": expire})
        if role:
            to_encode.update({"role": role})
        
        # 토큰 생성
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.security.SECRET_KEY, 
            algorithm=settings.security.ALGORITHM
        )
        
        logger.info(f"[JWTTokenService] 액세스 토큰 생성: 사용자={subject}, 만료={expire}")
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        subject: Union[str, Dict[str, Any]],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        리프레시 토큰 생성
        - 액세스 토큰 재발급을 위한 토큰
        - Redis에 저장하여 관리
        """
        to_encode = {}
        
        # 만료 시간 설정
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=settings.security.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # 페이로드 구성
        to_encode.update({"sub": str(subject), "exp": expire})
        
        # 토큰 생성
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.security.SECRET_KEY, 
            algorithm=settings.security.ALGORITHM
        )
        
        logger.info(f"[JWTTokenService] 리프레시 토큰 생성: 사용자={subject}, 만료={expire}")
        return encoded_jwt
    
    @staticmethod
    async def save_refresh_token(user_id: str, refresh_token: str) -> bool:
        """
        리프레시 토큰 저장
        - Redis에 토큰 저장
        """
        try:
            await RedisClient.save_refresh_token(
                user_id, 
                refresh_token, 
                settings.security.REFRESH_TOKEN_EXPIRE_DAYS
            )
            logger.info(f"[JWTTokenService] 리프레시 토큰 저장 성공: 사용자={user_id}")
            return True
        except Exception as e:
            logger.error(f"[JWTTokenService] 리프레시 토큰 저장 실패: {str(e)}")
            return False
    
    @staticmethod
    async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
        """
        리프레시 토큰 검증
        - Redis에 저장된 토큰과 비교
        """
        try:
            # 토큰 페이로드 검증
            payload = jwt.decode(
                refresh_token, 
                settings.security.SECRET_KEY, 
                algorithms=[settings.security.ALGORITHM]
            )
            token_sub = payload.get("sub")
            
            # 페이로드의 subject와 사용자 ID 비교
            if token_sub != user_id:
                logger.warning(f"[JWTTokenService] 토큰 사용자 불일치: token_sub={token_sub}, user_id={user_id}")
                return False
            
            # Redis에 저장된 토큰과 비교
            is_valid = await RedisClient.verify_refresh_token(user_id, refresh_token)
            if is_valid:
                logger.info(f"[JWTTokenService] 리프레시 토큰 검증 성공: 사용자={user_id}")
                return True
            else:
                logger.warning(f"[JWTTokenService] 리프레시 토큰 검증 실패: 사용자={user_id}")
                return False
                
        except JWTError as e:
            logger.warning(f"[JWTTokenService] 리프레시 토큰 디코딩 실패: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[JWTTokenService] 리프레시 토큰 검증 중 오류: {str(e)}")
            return False
    
    @staticmethod
    async def invalidate_refresh_token(user_id: str) -> bool:
        """
        리프레시 토큰 무효화
        - 로그아웃 시 호출
        """
        try:
            await RedisClient.delete_token(user_id)
            logger.info(f"[JWTTokenService] 리프레시 토큰 무효화 성공: 사용자={user_id}")
            return True
        except Exception as e:
            logger.error(f"[JWTTokenService] 리프레시 토큰 무효화 실패: {str(e)}")
            return False
    
    @staticmethod
    def verify_token(token: str) -> Optional[TokenPayload]:
        """
        토큰 검증 및 페이로드 추출
        - 토큰 유효성 검사 및 페이로드 반환
        - 유효하지 않은 토큰은 None 반환
        """
        try:
            # 토큰 디코딩
            payload = jwt.decode(
                token, 
                settings.security.SECRET_KEY, 
                algorithms=[settings.security.ALGORITHM]
            )
            
            token_data = TokenPayload(
                sub=payload.get("sub"),
                role=payload.get("role"),
                exp=payload.get("exp")
            )
            
            # 토큰 만료 확인
            if datetime.fromtimestamp(token_data.exp) < datetime.utcnow():
                logger.warning(f"[JWTTokenService] 토큰 만료됨: {token_data.sub}")
                return None
                
            logger.debug(f"[JWTTokenService] 토큰 검증 성공: {token_data.sub}")
            return token_data
            
        except JWTError as e:
            logger.warning(f"[JWTTokenService] 토큰 검증 실패: {e}")
            return None
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        비밀번호 검증
        - 평문 비밀번호와 해시된 비밀번호 비교
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        비밀번호 해싱
        - 평문 비밀번호를 bcrypt로 해싱
        """
        return pwd_context.hash(password)

    @staticmethod
    def validate_password(password: str) -> bool:
        """
        비밀번호 정책 검증
        - 길이, 대소문자, 숫자, 특수문자 요구사항 확인
        """
        # 길이 검증
        if (len(password) < settings.security.PASSWORD_MIN_LENGTH or 
            len(password) > settings.security.PASSWORD_MAX_LENGTH):
            return False
        
        # 대문자 포함 검증
        if settings.security.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False
        
        # 소문자 포함 검증
        if settings.security.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False
        
        # 숫자 포함 검증
        if settings.security.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            return False
        
        # 특수문자 포함 검증
        if settings.security.PASSWORD_REQUIRE_SPECIAL and not any(not c.isalnum() for c in password):
            return False
        
        return True