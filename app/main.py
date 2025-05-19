"""
애플리케이션 메인 파일 (FastAPI-Flow with Security)
- 앱 초기화 및 설정
- 라우터 등록
- 미들웨어 등록
- 보안 기능 추가
"""
import os
import asyncio
import logging
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

# 프로젝트 컴포넌트 임포트
from app.middleware.logging import logging_middleware
from app.middleware.security import security_middleware, rate_limit_middleware, xss_protection_middleware
from app.router.hello import router as hello_router
from app.router.auth import router as auth_router
from app.router.protected import router as protected_router
from app.router.security_test import router as security_test_router
from app.exception.global_handler import register_exception_handlers
from app.dependency.auth import log_request
from app.config.redis import RedisClient
from app.config.settings import get_settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 설정 가져오기
settings = get_settings()

# 애플리케이션 시작/종료 시 실행할 코드
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리
    - 시작 시점에 리소스 초기화 (Redis 연결 등)
    - 종료 시점에 리소스 정리 (연결 종료 등)
    """
    # 애플리케이션 시작 시 실행
    logger.info("🚀 애플리케이션 시작 - 리소스 초기화 중...")
    
    # Redis 초기화
    try:
        await RedisClient.initialize()
        logger.info("✅ Redis 연결 초기화 완료")
    except Exception as e:
        logger.warning(f"⚠️ Redis 연결 실패 (애플리케이션은 계속 실행됩니다): {str(e)}")
        logger.warning("⚠️ 리프레시 토큰 기능이 제한될 수 있습니다.")
    
    # 다른 리소스 초기화 (DB 연결 등)
    # ...
    
    logger.info("✅ 애플리케이션 초기화 완료")
    
    # FastAPI 애플리케이션 실행
    yield
    
    # 애플리케이션 종료 시 실행
    logger.info("🛑 애플리케이션 종료 - 리소스 정리 중...")
    
    # Redis 연결 종료
    try:
        await RedisClient.close()
        logger.info("✅ Redis 연결 정리 완료")
    except Exception as e:
        logger.error(f"❌ Redis 연결 종료 중 오류: {str(e)}")
    
    # 다른 리소스 정리
    # ...
    
    logger.info("👋 애플리케이션 정상 종료")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    # 전역 의존성 설정 예시 (모든 엔드포인트에 적용)
    # dependencies=[Depends(log_request)]
)

# CORS 미들웨어 등록
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.security.CORS_METHODS,
    allow_headers=settings.security.CORS_HEADERS,
)

# 보안 미들웨어 등록
app.middleware("http")(security_middleware)
app.middleware("http")(xss_protection_middleware)
app.middleware("http")(rate_limit_middleware)

# 커스텀 로깅 미들웨어 등록
app.middleware("http")(logging_middleware)

# 기존 라우터 등록
app.include_router(hello_router)

# 새로운 보안 관련 라우터 등록
app.include_router(auth_router)
app.include_router(protected_router)
app.include_router(security_test_router)

# 글로벌 예외 핸들러 등록
register_exception_handlers(app)

# 루트 엔드포인트
@app.get("/")
async def root():
    """
    루트 경로 처리
    - 애플리케이션 기본 정보 반환
    """
    return {
        "app": settings.APP_NAME,
        "description": settings.DESCRIPTION,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "environment": settings.ENV,
        "endpoints": [
            # 기존 API
            {
                "path": "/api/hello",
                "description": "기본 Hello 엔드포인트"
            },
            # 보안 테스트 API
            {
                "path": "/api/security-test/public",
                "description": "공개 보안 테스트 엔드포인트"
            },
            {
                "path": "/api/security-test/jwt-auth",
                "description": "JWT 인증 테스트 (Bearer 토큰 필요)"
            },
            # 인증 API
            {
                "path": "/api/auth/login",
                "description": "로그인 (인증 토큰 발급)"
            },
            {
                "path": "/api/auth/register",
                "description": "회원가입"
            },
            # 보호된 API 
            {
                "path": "/api/protected/me",
                "description": "인증된 사용자 정보 조회 (인증 필요)"
            },
            {
                "path": "/api/protected/admin",
                "description": "관리자 전용 API (ADMIN 역할 필요)"
            }
        ]
    }

# 상태 확인 엔드포인트
@app.get("/health")
async def health_check():
    """
    상태 확인 엔드포인트
    - 애플리케이션 및 종속 서비스 상태 확인
    - 모니터링 및 컨테이너 헬스 체크에 활용
    """
    # 상태 정보 수집
    status = {
        "status": "UP",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENV,
        "components": {
            "app": {"status": "UP"}
        }
    }
    
    # Redis 상태 확인
    try:
        redis = await RedisClient.get_client()
        await redis.ping()
        status["components"]["redis"] = {"status": "UP"}
    except Exception as e:
        status["components"]["redis"] = {
            "status": "DOWN", 
            "error": str(e)
        }
        # 중요 컴포넌트가 다운된 경우 전체 상태도 DOWN으로 설정
        # status["status"] = "DOWN"
    
    # 다른 컴포넌트 상태 확인
    # DB, 외부 API 등
    
    return status

# 메인 실행 함수 (애플리케이션 직접 실행 시)
if __name__ == "__main__":
    """
    메인 실행 함수
    - 직접 실행 시 Uvicorn ASGI 서버 시작
    """
    import uvicorn
    
    # 환경 변수에서 설정 로드 (또는 기본값 사용)
    host = settings.HOST
    port = settings.PORT
    reload = settings.RELOAD
    
    logger.info(f"🚀 Uvicorn ASGI 서버 시작 중... (host={host}, port={port}, reload={reload})")
    
    # Uvicorn 서버 설정 및 시작
    uvicorn.run(
        "app.main:app",  # 애플리케이션 임포트 경로
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )