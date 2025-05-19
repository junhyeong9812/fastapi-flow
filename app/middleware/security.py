"""
✅ 보안 미들웨어
- Spring Security의 필터와 유사한 역할
- 모든 요청에 대한 보안 헤더 추가
- CORS 처리 및 기타 보안 기능 구현
"""
from fastapi import Request, Response
from typing import Callable, Dict
import logging
import time
from app.config.settings import get_settings

# 로깅 설정
logger = logging.getLogger(__name__)

# 설정 가져오기
settings = get_settings()

async def security_middleware(request: Request, call_next: Callable) -> Response:
    """
    보안 미들웨어
    - Spring Security의 보안 헤더 필터와 유사한 역할
    - 모든 응답에 보안 헤더 추가
    - 요청 검증 및 필터링
    """
    # 요청 시작 시간 기록
    start_time = time.time()
    
    # 요청 정보 로깅
    method = request.method
    path = request.url.path
    client_ip = request.client.host if request.client else "Unknown"
    
    logger.debug(f"[SecurityMiddleware] 요청: [{method}] {path} from {client_ip}")
    
    # 잠재적인 보안 검증 로직
    # (예: 특정 IP 차단, 사용자 에이전트 검증 등)
    
    try:
        # 다음 미들웨어 또는 라우터로 요청 전달
        response = await call_next(request)
        
        # 보안 헤더 추가
        for header_name, header_value in settings.security.SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
        
        # 추가 보안 헤더 설정
        # CORS 헤더는 CORSMiddleware에서 처리
        
        # 처리 시간 계산
        process_time = time.time() - start_time
        
        # 응답 정보 로깅
        status_code = response.status_code
        logger.debug(f"[SecurityMiddleware] 응답: [{method}] {path} - {status_code} - {process_time:.4f}초")
        
        return response
    
    except Exception as e:
        # 예외 발생 시 로깅
        process_time = time.time() - start_time
        logger.error(f"[SecurityMiddleware] 예외 발생: [{method}] {path} - {str(e)} - {process_time:.4f}초")
        # 예외를 다시 발생시켜 글로벌 예외 핸들러가 처리하도록 함
        raise


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    속도 제한 미들웨어
    - Spring의 RateLimiter와 유사한 역할
    - 클라이언트 IP 기반 요청 속도 제한
    - Redis 기반 카운터 구현
    
    참고: 실제 구현에서는 Redis를 사용하여 카운터 관리
    """
    # 클라이언트 IP 추출
    client_ip = request.client.host if request.client else "Unknown"
    
    # 실제 구현에서는 Redis를 사용하여 카운터 관리
    # 예시: Redis Key = "rate_limit:{client_ip}"
    
    # 현재는 간단한 로깅만 수행
    logger.debug(f"[RateLimitMiddleware] 요청: {client_ip}")
    
    # 다음 미들웨어 또는 라우터로 요청 전달
    return await call_next(request)


async def xss_protection_middleware(request: Request, call_next: Callable) -> Response:
    """
    XSS 보호 미들웨어
    - Spring Security의 XSS 보호 기능과 유사
    - 응답 본문의 XSS 취약점 필터링 (Content-Security-Policy 헤더 활용)
    
    참고: 기본적인 XSS 보호는 CSP 헤더로 처리되지만,
    더 강력한 보호가 필요할 경우 응답 본문 필터링도 구현할 수 있음
    """
    # 다음 미들웨어 또는 라우터로 요청 전달
    response = await call_next(request)
    
    # 기본 XSS 보호 헤더 추가
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Content-Security-Policy 헤더 추가
    # 이미 security_middleware에서 추가되었다면 건너뜀
    if "Content-Security-Policy" not in response.headers:
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response