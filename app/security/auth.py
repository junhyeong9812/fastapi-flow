"""
✅ 인증 및 권한 의존성
- Spring Security의 인증/인가 필터와 유사한 역할
- 토큰 기반 인증 및 역할 기반 권한 검사
- FastAPI의 Depends를 활용한 인증 흐름 구현
"""
from fastapi import Depends, HTTPException, status, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Callable, Dict, Any
import logging

from app.security.jwt import JWTTokenService, TokenPayload
from app.exception.global_handler import AppException

# 로깅 설정
logger = logging.getLogger(__name__)

# Bearer 토큰 스키마
bearer_scheme = HTTPBearer(
    auto_error=False,  # 토큰 누락 시 자동 오류 비활성화 (커스텀 처리를 위해)
    description="JWT 인증 토큰"
)

class AuthDependency:
    """
    인증 및 권한 의존성 클래스
    - Spring Security의 SecurityConfig + Filter와 유사한 역할
    - 다양한 인증 및 권한 검사 의존성 함수 제공
    - 의존성 주입 방식으로 라우터에 적용
    """
    
    @staticmethod
    async def get_token_payload(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
    ) -> TokenPayload:
        """
        토큰 페이로드 추출 의존성
        - Bearer 토큰에서 페이로드 추출 및 검증
        - 유효하지 않은 토큰인 경우 401 Unauthorized 오류 발생
        """
        # 토큰이 없는 경우
        if credentials is None:
            logger.warning("[AuthDependency] 인증 토큰 누락")
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="인증 토큰이 필요합니다",
                error_code="MISSING_TOKEN"
            )
        
        # 토큰 검증
        token_payload = JWTTokenService.verify_token(credentials.credentials)
        if token_payload is None:
            logger.warning("[AuthDependency] 유효하지 않은 토큰")
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="유효하지 않은 인증 토큰입니다",
                error_code="INVALID_TOKEN"
            )
        
        logger.info(f"[AuthDependency] 인증 성공: 사용자={token_payload.sub}")
        return token_payload
    
    @staticmethod
    async def get_current_user(
        token_payload: TokenPayload = Depends(get_token_payload)
    ) -> Dict[str, Any]:
        """
        현재 사용자 정보 추출 의존성
        - 토큰 페이로드에서 사용자 정보 추출
        - Spring Security의 @AuthenticationPrincipal과 유사
        
        사용 예시:
        @router.get("/me")
        async def get_me(current_user: dict = Depends(AuthDependency.get_current_user)):
            return current_user
        """
        # 실제 구현에서는 DB에서 사용자 정보 조회 가능
        # 여기서는 간단한 예시로 토큰 정보만 반환
        user_info = {
            "id": token_payload.sub,
            "role": token_payload.role or "USER"
        }
        
        return user_info
    
    @staticmethod
    def has_role(required_role: str) -> Callable:
        """
        역할 기반 권한 검사 의존성 팩토리
        - Spring Security의 @PreAuthorize("hasRole('ROLE_xxx')")와 유사
        - 특정 역할을 가진 사용자만 접근 허용
        
        사용 예시:
        @router.get("/admin", dependencies=[Depends(AuthDependency.has_role("ADMIN"))])
        async def admin_only():
            return {"message": "관리자 전용 API"}
        """
        async def role_checker(
            current_user: Dict[str, Any] = Depends(AuthDependency.get_current_user)
        ) -> None:
            user_role = current_user.get("role", "").upper()
            required_upper = required_role.upper()
            
            logger.info(f"[AuthDependency] 권한 검사: 필요={required_upper}, 현재={user_role}")
            
            if user_role != required_upper:
                logger.warning(f"[AuthDependency] 권한 부족: {user_role} ≠ {required_upper}")
                raise AppException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=f"{required_role} 권한이 필요합니다",
                    error_code="INSUFFICIENT_PERMISSIONS"
                )
        
        return role_checker
    
    @staticmethod
    def check_permissions(permissions: List[str]) -> Callable:
        """
        권한 목록 검사 의존성 팩토리
        - Spring Security의 @PreAuthorize("hasAuthority('xxx')")와 유사
        - 특정 권한을 가진 사용자만 접근 허용
        
        사용 예시:
        @router.get("/items", dependencies=[Depends(AuthDependency.check_permissions(["READ_ITEMS"]))])
        async def get_items():
            return {"items": ["item1", "item2"]}
        """
        async def permission_checker(
            current_user: Dict[str, Any] = Depends(AuthDependency.get_current_user)
        ) -> None:
            # 실제 구현에서는 사용자 권한 목록을 DB에서 조회
            # 여기서는 간단한 예시로 역할 기반으로 권한 체크
            user_role = current_user.get("role", "").upper()
            
            # 관리자는 모든 권한 보유
            if user_role == "ADMIN":
                return
            
            # 권한 체크 (실제로는 DB에서 사용자별 권한 목록 조회)
            user_permissions = []
            if user_role == "USER":
                user_permissions = ["READ_ITEMS"]
            elif user_role == "EDITOR":
                user_permissions = ["READ_ITEMS", "WRITE_ITEMS"]
            
            # 필요한 모든 권한을 가지고 있는지 확인
            has_all_permissions = all(perm in user_permissions for perm in permissions)
            
            if not has_all_permissions:
                logger.warning(f"[AuthDependency] 권한 부족: 필요={permissions}, 보유={user_permissions}")
                raise AppException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="필요한 권한이 없습니다",
                    error_code="INSUFFICIENT_PERMISSIONS",
                    details={"required": permissions}
                )
        
        return permission_checker
    
    @staticmethod
    async def verify_csrf_token(request: Request) -> None:
        """
        CSRF 토큰 검증 의존성
        - Spring Security의 CSRF 보호와 유사
        - POST, PUT, DELETE 메서드에 대해 CSRF 토큰 검증
        """
        # CSRF 검증이 필요한 메서드인지 확인
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # 헤더에서 CSRF 토큰 추출
            csrf_token = request.headers.get("X-CSRF-Token")
            
            # 세션에서 저장된 토큰 추출 (실제로는 세션 관리 시스템 필요)
            # session_token = request.session.get("csrf_token")
            session_token = None  # 예시로 None 설정
            
            # CSRF 토큰 검증
            if csrf_token is None or session_token is None or csrf_token != session_token:
                logger.warning("[AuthDependency] CSRF 토큰 검증 실패")
                raise AppException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="유효하지 않은 CSRF 토큰입니다",
                    error_code="INVALID_CSRF_TOKEN"
                )
            
            logger.info("[AuthDependency] CSRF 토큰 검증 성공")

    @staticmethod
    def is_resource_owner(param_name: str) -> Callable:
        """
        리소스 소유자 확인 의존성 팩토리
        - Spring Security의 @PreAuthorize("#id == authentication.principal.id")와 유사
        - 경로 파라미터의 ID가 현재 로그인한 사용자의 ID와 일치하는지 확인
        
        사용 예시:
        @router.get("/users/{user_id}", dependencies=[Depends(AuthDependency.is_resource_owner("user_id"))])
        async def get_user(user_id: str):
            return {"id": user_id, "message": "자신의 정보만 볼 수 있습니다"}
        """
        async def owner_checker(
            request: Request,
            current_user: Dict[str, Any] = Depends(AuthDependency.get_current_user)
        ) -> None:
            # 경로 파라미터에서 ID 추출
            resource_id = request.path_params.get(param_name)
            user_id = current_user.get("id")
            
            # 관리자는 모든 리소스에 접근 가능
            if current_user.get("role", "").upper() == "ADMIN":
                logger.info(f"[AuthDependency] 관리자 권한으로 리소스 접근: {resource_id}")
                return
            
            # ID 일치 여부 확인
            if resource_id != user_id:
                logger.warning(f"[AuthDependency] 리소스 소유자 불일치: resource_id={resource_id}, user_id={user_id}")
                raise AppException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="본인의 리소스만 접근할 수 있습니다",
                    error_code="NOT_RESOURCE_OWNER"
                )
                
            logger.info(f"[AuthDependency] 리소스 소유자 확인 성공: {resource_id}")
        
        return owner_checker

# 간편한 라우터 보호를 위한 의존성
auth_required = Depends(AuthDependency.get_token_payload)
get_current_user = Depends(AuthDependency.get_current_user)

"""
🔍 사용 예시:

1. 기본 인증 요구:
@router.get("/protected", dependencies=[auth_required])
async def protected_route():
    return {"message": "인증된 사용자만 접근 가능"}

2. 현재 사용자 정보 사용:
@router.get("/me")
async def get_me(current_user: dict = get_current_user):
    return {"user": current_user}

3. 역할 기반 접근 제어:
@router.get("/admin", dependencies=[Depends(AuthDependency.has_role("ADMIN"))])
async def admin_only():
    return {"message": "관리자 전용 API"}

4. 권한 기반 접근 제어:
@router.get("/items/create", dependencies=[Depends(AuthDependency.check_permissions(["WRITE_ITEMS"]))])
async def create_item():
    return {"message": "아이템 생성 권한이 있습니다"}

5. 리소스 소유자 확인:
@router.get("/users/{user_id}", dependencies=[Depends(AuthDependency.is_resource_owner("user_id"))])
async def get_user(user_id: str):
    return {"id": user_id, "message": "자신의 정보만 볼 수 있습니다"}
"""