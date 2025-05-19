"""
✅ 인증 라우터
- 사용자 등록, 로그인, 토큰 갱신 등 인증 관련 API 제공
- Spring Security의 AuthenticationController와 유사한 역할
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any, Optional
import logging
import uuid
from datetime import datetime

from app.security.jwt import JWTTokenService, TokenPayload
from app.models.user import UserLogin, UserCreate, UserResponse, TokenResponse, RefreshTokenRequest
from app.exception.global_handler import AppException
from app.config.redis import RedisClient

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/api/auth",
    tags=["인증"],
    responses={
        401: {"description": "인증 실패"},
        403: {"description": "권한 없음"},
    }
)

# 간단한 메모리 기반 사용자 저장소 (실제로는 데이터베이스 사용)
users_db = {}

# 초기 사용자 데이터 설정
def init_users():
    # 관리자 계정
    admin_id = str(uuid.uuid4())
    admin_password_hash = JWTTokenService.get_password_hash("admin123")
    users_db[admin_id] = {
        "id": admin_id,
        "username": "admin",
        "password": admin_password_hash,
        "email": "admin@example.com",
        "full_name": "관리자",
        "role": "ADMIN",
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    # 일반 사용자 계정
    user_id = str(uuid.uuid4())
    user_password_hash = JWTTokenService.get_password_hash("user123")
    users_db[user_id] = {
        "id": user_id,
        "username": "user",
        "password": user_password_hash,
        "email": "user@example.com",
        "full_name": "일반 사용자",
        "role": "USER",
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    logger.info(f"[AuthRouter] 초기 사용자 데이터 설정 완료 (관리자: {admin_id}, 사용자: {user_id})")

# 초기 사용자 데이터 설정
init_users()

# 사용자 인증 함수
async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    사용자 인증
    - 아이디/비밀번호로 사용자 인증
    - 인증 성공 시 사용자 정보 반환, 실패 시 None 반환
    """
    logger.info(f"[AuthRouter] 사용자 인증 시도: {username}")
    
    # 사용자명으로 사용자 찾기
    user = None
    for u in users_db.values():
        if u["username"] == username:
            user = u
            break
    
    # 사용자가 없는 경우
    if user is None:
        logger.warning(f"[AuthRouter] 사용자 없음: {username}")
        return None
    
    # 비밀번호 검증
    if not JWTTokenService.verify_password(password, user["password"]):
        logger.warning(f"[AuthRouter] 비밀번호 불일치: {username}")
        return None
    
    # 마지막 로그인 시간 업데이트
    user["last_login"] = datetime.utcnow()
    
    logger.info(f"[AuthRouter] 인증 성공: {username}")
    return user

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> TokenResponse:
    """
    로그인 API
    - OAuth2 형식의 로그인 요청 처리
    - 액세스 토큰 및 리프레시 토큰 발급
    
    사용 예시:
    curl -X POST http://localhost:8000/api/auth/login -d "username=admin&password=admin123" -H "Content-Type: application/x-www-form-urlencoded"
    """
    logger.info(f"[AuthRouter] 로그인 요청: {form_data.username}")
    
    # 사용자 인증
    user = await authenticate_user(form_data.username, form_data.password)
    if user is None:
        logger.warning(f"[AuthRouter] 로그인 실패: {form_data.username}")
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="아이디 또는 비밀번호가 일치하지 않습니다",
            error_code="INVALID_CREDENTIALS"
        )
    
    # 액세스 토큰 생성
    access_token = JWTTokenService.create_access_token(
        subject=user["id"],
        role=user["role"]
    )
    
    # 리프레시 토큰 생성
    refresh_token = JWTTokenService.create_refresh_token(
        subject=user["id"]
    )
    
    # Redis에 리프레시 토큰 저장
    await RedisClient.save_refresh_token(user["id"], refresh_token)
    
    # 사용자 응답 모델 생성
    user_response = UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        full_name=user["full_name"] or "",
        role=user["role"],
        created_at=user["created_at"],
        last_login=user["last_login"]
    )
    
    # 토큰 응답 생성
    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_response
    )
    
    logger.info(f"[AuthRouter] 로그인 성공: {form_data.username}")
    return token_response

@router.post("/register", response_model=UserResponse)
async def register(
    user_create: UserCreate
) -> UserResponse:
    """
    회원가입 API
    - 새로운 사용자 등록
    - 중복 아이디/이메일 체크
    
    사용 예시:
    curl -X POST http://localhost:8000/api/auth/register -H "Content-Type: application/json" -d '{"username":"newuser","password":"password123","email":"new@example.com","full_name":"New User","role":"USER"}'
    """
    logger.info(f"[AuthRouter] 회원가입 요청: {user_create.username}")
    
    # 중복 아이디 체크
    for user in users_db.values():
        if user["username"] == user_create.username:
            logger.warning(f"[AuthRouter] 아이디 중복: {user_create.username}")
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"이미 사용 중인 아이디입니다: {user_create.username}",
                error_code="USERNAME_ALREADY_EXISTS"
            )
    
    # 중복 이메일 체크
    for user in users_db.values():
        if user["email"] == user_create.email:
            logger.warning(f"[AuthRouter] 이메일 중복: {user_create.email}")
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"이미 사용 중인 이메일입니다: {user_create.email}",
                error_code="EMAIL_ALREADY_EXISTS"
            )
    
    # 비밀번호 정책 검증
    if not JWTTokenService.validate_password(user_create.password):
        logger.warning(f"[AuthRouter] 비밀번호 정책 불충족: {user_create.username}")
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="비밀번호는 8자 이상이어야 하며, 대문자, 소문자, 숫자, 특수문자를 포함해야 합니다",
            error_code="INVALID_PASSWORD"
        )
    
    # 비밀번호 해싱
    hashed_password = JWTTokenService.get_password_hash(user_create.password)
    
    # 사용자 ID 생성
    user_id = str(uuid.uuid4())
    
    # 사용자 생성
    new_user = {
        "id": user_id,
        "username": user_create.username,
        "password": hashed_password,
        "email": user_create.email,
        "full_name": user_create.full_name,
        "role": user_create.role,
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    # 사용자 저장
    users_db[user_id] = new_user
    
    # 사용자 응답 모델 생성
    user_response = UserResponse(
        id=user_id,
        username=user_create.username,
        email=user_create.email,
        full_name=user_create.full_name or "",
        role=user_create.role,
        created_at=new_user["created_at"],
        last_login=None
    )
    
    logger.info(f"[AuthRouter] 회원가입 성공: {user_create.username}, ID={user_id}")
    return user_response

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest
) -> TokenResponse:
    """
    토큰 갱신 API
    - 리프레시 토큰으로 새 액세스 토큰 발급
    - Redis에 저장된 리프레시 토큰과 비교 검증
    
    사용 예시:
    curl -X POST http://localhost:8000/api/auth/refresh -H "Content-Type: application/json" -d '{"refresh_token":"your_refresh_token"}'
    """
    logger.info("[AuthRouter] 토큰 갱신 요청")
    
    # 리프레시 토큰 검증
    try:
        # 토큰 페이로드 추출
        payload = JWTTokenService.verify_token(refresh_request.refresh_token)
        if payload is None:
            logger.warning("[AuthRouter] 유효하지 않은 리프레시 토큰")
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="유효하지 않은 리프레시 토큰입니다",
                error_code="INVALID_REFRESH_TOKEN"
            )
        
        user_id = payload.sub
        
        # Redis에 저장된 토큰과 비교
        is_valid = await RedisClient.verify_refresh_token(user_id, refresh_request.refresh_token)
        if not is_valid:
            logger.warning(f"[AuthRouter] 저장된 리프레시 토큰과 불일치: {user_id}")
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="유효하지 않은 리프레시 토큰입니다",
                error_code="INVALID_REFRESH_TOKEN"
            )
        
        # 사용자 정보 조회
        if user_id not in users_db:
            logger.warning(f"[AuthRouter] 토큰의 사용자를 찾을 수 없음: {user_id}")
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="사용자를 찾을 수 없습니다",
                error_code="USER_NOT_FOUND"
            )
        
        user = users_db[user_id]
        
        # 새 액세스 토큰 생성
        access_token = JWTTokenService.create_access_token(
            subject=user["id"],
            role=user["role"]
        )
        
        # 사용자 응답 모델 생성
        user_response = UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"] or "",
            role=user["role"],
            created_at=user["created_at"],
            last_login=user["last_login"]
        )
        
        # 토큰 응답 생성
        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_request.refresh_token,  # 기존 리프레시 토큰 유지
            token_type="bearer",
            user=user_response
        )
        
        logger.info(f"[AuthRouter] 토큰 갱신 성공: {user['username']}")
        return token_response
        
    except Exception as e:
        logger.error(f"[AuthRouter] 토큰 갱신 실패: {str(e)}")
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="토큰 갱신에 실패했습니다",
            error_code="REFRESH_TOKEN_FAILED"
        )

@router.post("/logout")
async def logout(
    request: Request,
    token_payload: TokenPayload = Depends(JWTTokenService.verify_token)
) -> Dict[str, str]:
    """
    로그아웃 API
    - 리프레시 토큰 무효화
    - Redis에서 토큰 삭제
    
    사용 예시:
    curl -X POST http://localhost:8000/api/auth/logout -H "Authorization: Bearer your_access_token"
    """
    user_id = token_payload.sub
    logger.info(f"[AuthRouter] 로그아웃 요청: {user_id}")
    
    # Redis에서 리프레시 토큰 삭제
    await RedisClient.delete_token(user_id)
    
    logger.info(f"[AuthRouter] 로그아웃 성공: {user_id}")
    return {"message": "로그아웃 되었습니다"}