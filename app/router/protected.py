"""
✅ 보호된 API 라우터
- 인증이 필요한 API 엔드포인트 제공
- 역할 기반 권한 관리 적용
- Spring Security의 보호된 컨트롤러와 유사한 역할
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List
import logging

from app.security.auth import AuthDependency
from app.security.jwt import TokenPayload

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/api/protected",
    tags=["보호된 API"],
    dependencies=[Depends(AuthDependency.get_token_payload)],  # 기본 인증 의존성 설정
    responses={
        401: {"description": "인증 실패"},
        403: {"description": "권한 없음"},
    }
)

@router.get("/me")
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(AuthDependency.get_current_user)
) -> Dict[str, Any]:
    """
    현재 사용자 정보 조회 API
    - 인증된 사용자 정보 반환
    - Spring Security의 @AuthenticationPrincipal 활용과 유사
    
    사용 예시:
    curl -X GET http://localhost:8000/api/protected/me -H "Authorization: Bearer your_access_token"
    """
    logger.info(f"[ProtectedRouter] 현재 사용자 정보 조회: {current_user['id']}")
    return {
        "user_id": current_user["id"],
        "role": current_user["role"],
        "message": "인증된 사용자입니다"
    }

@router.get("/admin", dependencies=[Depends(AuthDependency.has_role("ADMIN"))])
async def admin_only() -> Dict[str, str]:
    """
    관리자 전용 API
    - ADMIN 역할을 가진 사용자만 접근 가능
    - Spring Security의 @PreAuthorize("hasRole('ADMIN')") 활용과 유사
    
    사용 예시:
    curl -X GET http://localhost:8000/api/protected/admin -H "Authorization: Bearer admin_access_token"
    """
    logger.info("[ProtectedRouter] 관리자 전용 API 호출")
    return {"message": "관리자 전용 API 접근 성공"}

@router.get("/items", dependencies=[Depends(AuthDependency.check_permissions(["READ_ITEMS"]))])
async def get_items() -> Dict[str, List[str]]:
    """
    아이템 목록 조회 API
    - READ_ITEMS 권한을 가진 사용자만 접근 가능
    - Spring Security의 @PreAuthorize("hasAuthority('READ_ITEMS')") 활용과 유사
    
    사용 예시:
    curl -X GET http://localhost:8000/api/protected/items -H "Authorization: Bearer your_access_token"
    """
    logger.info("[ProtectedRouter] 아이템 목록 조회")
    return {"items": ["Item 1", "Item 2", "Item 3"]}

@router.get("/users/{user_id}", dependencies=[Depends(AuthDependency.is_resource_owner("user_id"))])
async def get_user_by_id(user_id: str) -> Dict[str, Any]:
    """
    사용자 정보 조회 API
    - 자신의 정보만 조회 가능
    - 관리자는 모든 사용자 정보 조회 가능
    - Spring Security의 @PreAuthorize("#id == authentication.principal.id") 활용과 유사
    
    사용 예시:
    curl -X GET http://localhost:8000/api/protected/users/your_user_id -H "Authorization: Bearer your_access_token"
    """
    logger.info(f"[ProtectedRouter] 사용자 정보 조회: {user_id}")
    return {
        "id": user_id,
        "message": "자신의 정보만 조회할 수 있습니다",
        "timestamp": "2023-01-01T00:00:00"
    }

# 생성, 수정, 삭제 API 예시
@router.post("/items", dependencies=[Depends(AuthDependency.check_permissions(["WRITE_ITEMS"]))])
async def create_item(
    item: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(AuthDependency.get_current_user)
) -> Dict[str, Any]:
    """
    아이템 생성 API
    - WRITE_ITEMS 권한을 가진 사용자만 접근 가능
    
    사용 예시:
    curl -X POST http://localhost:8000/api/protected/items -H "Authorization: Bearer your_access_token" -H "Content-Type: application/json" -d '{"name":"New Item"}'
    """
    logger.info(f"[ProtectedRouter] 아이템 생성: {item.get('name')}, 사용자: {current_user['id']}")
    return {
        "id": "item_123",
        "name": item.get("name"),
        "created_by": current_user["id"],
        "message": "아이템 생성 성공"
    }

@router.put("/items/{item_id}", dependencies=[Depends(AuthDependency.has_role("ADMIN"))])
async def update_item(
    item_id: str,
    item: Dict[str, Any]
) -> Dict[str, Any]:
    """
    아이템 수정 API
    - 관리자 역할을 가진 사용자만 접근 가능
    
    사용 예시:
    curl -X PUT http://localhost:8000/api/protected/items/item_123 -H "Authorization: Bearer admin_access_token" -H "Content-Type: application/json" -d '{"name":"Updated Item"}'
    """
    logger.info(f"[ProtectedRouter] 아이템 수정: {item_id}, 내용: {item}")
    return {
        "id": item_id,
        "name": item.get("name"),
        "message": "아이템 수정 성공"
    }

@router.delete("/items/{item_id}", dependencies=[Depends(AuthDependency.has_role("ADMIN"))])
async def delete_item(item_id: str) -> Dict[str, str]:
    """
    아이템 삭제 API
    - 관리자 역할을 가진 사용자만 접근 가능
    
    사용 예시:
    curl -X DELETE http://localhost:8000/api/protected/items/item_123 -H "Authorization: Bearer admin_access_token"
    """
    logger.info(f"[ProtectedRouter] 아이템 삭제: {item_id}")
    return {"message": f"아이템 {item_id} 삭제 성공"}