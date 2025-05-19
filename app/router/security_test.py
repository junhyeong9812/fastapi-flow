"""
✅ 보안 테스트 라우터
- 보안 기능 테스트를 위한 엔드포인트 제공
- JWT 토큰 인증, 역할 기반 권한 등 테스트
- 기존 코드와 독립적으로 작동
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List
import logging

from app.security.auth import AuthDependency
from app.security.jwt import JWTTokenService, TokenPayload

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/api/security-test",
    tags=["보안 테스트"],
    responses={
        401: {"description": "인증 실패"},
        403: {"description": "권한 없음"},
    }
)

@router.get("/public")
async def public_endpoint() -> Dict[str, str]:
    """
    공개 엔드포인트
    - 인증 없이 누구나 접근 가능
    
    사용 예시:
    curl -X GET http://localhost:8000/api/security-test/public
    """
    logger.info("[SecurityTestRouter] 공개 엔드포인트 호출")
    return {"message": "누구나 접근 가능한 공개 엔드포인트입니다."}

@router.get("/jwt-auth", dependencies=[Depends(AuthDependency.get_token_payload)])
async def jwt_auth_test() -> Dict[str, str]:
    """
    JWT 인증 테스트 엔드포인트
    - 유효한 JWT 토큰이 필요
    
    사용 예시:
    curl -X GET http://localhost:8000/api/security-test/jwt-auth -H "Authorization: Bearer your_jwt_token"
    """
    logger.info("[SecurityTestRouter] JWT 인증 테스트 엔드포인트 호출")
    return {"message": "JWT 인증 성공! 이 메시지는 유효한 JWT 토큰이 있는 사용자만 볼 수 있습니다."}

@router.get("/user-info")
async def user_info_test(
    current_user: Dict[str, Any] = Depends(AuthDependency.get_current_user)
) -> Dict[str, Any]:
    """
    현재 사용자 정보 테스트 엔드포인트
    - 인증된 사용자 정보 반환
    
    사용 예시:
    curl -X GET http://localhost:8000/api/security-test/user-info -H "Authorization: Bearer your_jwt_token"
    """
    logger.info(f"[SecurityTestRouter] 사용자 정보 테스트 엔드포인트 호출: {current_user['id']}")
    return {
        "message": "인증된 사용자 정보입니다.",
        "user_id": current_user["id"],
        "role": current_user["role"]
    }

@router.get("/admin-only", dependencies=[Depends(AuthDependency.has_role("ADMIN"))])
async def admin_only_test() -> Dict[str, str]:
    """
    관리자 전용 테스트 엔드포인트
    - ADMIN 역할을 가진 사용자만 접근 가능
    
    사용 예시:
    curl -X GET http://localhost:8000/api/security-test/admin-only -H "Authorization: Bearer admin_jwt_token"
    """
    logger.info("[SecurityTestRouter] 관리자 전용 테스트 엔드포인트 호출")
    return {"message": "관리자 권한 확인 성공! 이 메시지는 ADMIN 역할을 가진 사용자만 볼 수 있습니다."}

@router.get("/permission-test", dependencies=[Depends(AuthDependency.check_permissions(["READ_DATA"]))])
async def permission_test() -> Dict[str, str]:
    """
    권한 테스트 엔드포인트
    - READ_DATA 권한을 가진 사용자만 접근 가능
    
    사용 예시:
    curl -X GET http://localhost:8000/api/security-test/permission-test -H "Authorization: Bearer your_jwt_token"
    """
    logger.info("[SecurityTestRouter] 권한 테스트 엔드포인트 호출")
    return {"message": "권한 확인 성공! 이 메시지는 READ_DATA 권한을 가진 사용자만 볼 수 있습니다."}

@router.get("/resource/{resource_id}", dependencies=[Depends(AuthDependency.is_resource_owner("resource_id"))])
async def resource_owner_test(resource_id: str) -> Dict[str, str]:
    """
    리소스 소유자 테스트 엔드포인트
    - 리소스 ID가 현재 사용자 ID와 일치하는 경우만 접근 가능
    - 관리자는 모든 리소스에 접근 가능
    
    사용 예시:
    curl -X GET http://localhost:8000/api/security-test/resource/your_user_id -H "Authorization: Bearer your_jwt_token"
    """
    logger.info(f"[SecurityTestRouter] 리소스 소유자 테스트 엔드포인트 호출: {resource_id}")
    return {
        "message": "리소스 소유자 확인 성공! 이 메시지는 해당 리소스의 소유자만 볼 수 있습니다.",
        "resource_id": resource_id
    }

@router.get("/security-headers-test")
async def security_headers_test() -> Dict[str, str]:
    """
    보안 헤더 테스트 엔드포인트
    - 응답에 보안 헤더가 추가되는지 확인
    
    사용 예시:
    curl -X GET http://localhost:8000/api/security-test/security-headers-test -v
    """
    logger.info("[SecurityTestRouter] 보안 헤더 테스트 엔드포인트 호출")
    return {"message": "응답 헤더에 X-Frame-Options, Content-Security-Policy 등의 보안 헤더가 추가되었는지 확인하세요."}

@router.get("/token-info")
async def token_info_test(
    token_payload: TokenPayload = Depends(AuthDependency.get_token_payload)
) -> Dict[str, Any]:
    """
    토큰 정보 테스트 엔드포인트
    - JWT 토큰 페이로드 정보 반환
    
    사용 예시:
    curl -X GET http://localhost:8000/api/security-test/token-info -H "Authorization: Bearer your_jwt_token"
    """
    logger.info(f"[SecurityTestRouter] 토큰 정보 테스트 엔드포인트 호출: {token_payload.sub}")
    return {
        "subject": token_payload.sub,
        "role": token_payload.role,
        "expires_at": token_payload.exp
    }