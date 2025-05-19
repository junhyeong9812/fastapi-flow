import os
import asyncio
import logging
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

# 프로젝트 컴포넌트 임포트
from app.middleware.logging import logging_middleware
from app.router.hello import router as hello_router
from app.exception.global_handler import register_exception_handlers
from app.dependency.auth import log_request

"""
✅ FastAPI 애플리케이션 엔트리포인트
- Spring의 DispatcherServlet과 대응되는 개념
- 애플리케이션 설정, 미들웨어 등록, 라우터 관리 담당
- 요청 처리의 출발점

🔍 주요 기능:
- 라이프사이클 이벤트 관리 (시작 시/종료 시 처리)
- 미들웨어 등록 (Filter 대응)
- 라우터 등록 (Controller 대응)
- 전역 예외 핸들러 등록 (@ControllerAdvice 대응)
- ASGI 서버 실행 (Embedded Tomcat 대응)
"""

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 애플리케이션 시작/종료 시 실행할 코드 (Spring의 @PostConstruct, @PreDestroy와 유사)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리
    - Spring의 @PostConstruct, @PreDestroy와 유사한 역할
    - 시작 시점에 리소스 초기화 (DB 연결, 캐시 등)
    - 종료 시점에 리소스 정리 (연결 종료 등)
    """
    # 애플리케이션 시작 시 실행 (Spring의 @PostConstruct와 유사)
    logger.info("🚀 애플리케이션 시작 - 리소스 초기화 중...")
    
    # 리소스 초기화 예시 (DB 연결 등)
    # db = await initialize_db_connection()
    # app.state.db = db
    
    # Redis 연결 예시
    # redis = await initialize_redis_connection()
    # app.state.redis = redis
    
    # 백그라운드 작업 시작 예시
    # background_task = asyncio.create_task(background_job())
    # app.state.background_task = background_task
    
    logger.info("✅ 애플리케이션 초기화 완료")
    
    # FastAPI 애플리케이션 실행
    yield
    
    # 애플리케이션 종료 시 실행 (Spring의 @PreDestroy와 유사)
    logger.info("🛑 애플리케이션 종료 - 리소스 정리 중...")
    
    # 리소스 정리 예시
    # await app.state.db.close()
    
    # Redis 연결 종료 예시
    # await app.state.redis.close()
    
    # 백그라운드 작업 취소 예시
    # app.state.background_task.cancel()
    # try:
    #     await app.state.background_task
    # except asyncio.CancelledError:
    #     pass
    
    logger.info("👋 애플리케이션 정상 종료")


# FastAPI 앱 생성 (라이프사이클 관리자 설정)
app = FastAPI(
    title="FastAPI-Flow",
    description="Spring MVC 패턴을 FastAPI로 구현한 학습용 프로젝트",
    version="0.1.0",
    lifespan=lifespan,
    # 전역 의존성 설정 예시 (모든 엔드포인트에 적용)
    # dependencies=[Depends(log_request)]
)

# CORS 미들웨어 등록 (Spring의 CorsFilter와 유사)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 프로덕션에서는 구체적인 오리진 지정 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 커스텀 로깅 미들웨어 등록 (Spring의 Filter와 유사)
# 미들웨어는 마지막에 추가한 것이 가장 먼저 실행됨 (Spring과 반대)
app.middleware("http")(logging_middleware)

# 라우터 등록 (Spring의 @Controller와 유사)
app.include_router(hello_router)

# 글로벌 예외 핸들러 등록 (Spring의 @ControllerAdvice와 유사)
register_exception_handlers(app)

# 루트 엔드포인트
@app.get("/")
async def root():
    """
    루트 경로 처리
    - 애플리케이션 기본 정보 반환
    """
    return {
        "app": "FastAPI-Flow",
        "description": "Spring MVC 패턴을 FastAPI로 구현한 학습용 프로젝트",
        "endpoints": [
            {
                "path": "/api/hello",
                "description": "기본 Hello 엔드포인트"
            },
            {
                "path": "/api/hello/{name}",
                "description": "이름을 받는 Hello 엔드포인트"
            },
            {
                "path": "/api/hello-query?name=value",
                "description": "쿼리 매개변수를 받는 Hello 엔드포인트"
            },
            {
                "path": "/api/hello-auth",
                "description": "인증이 필요한 Hello 엔드포인트 (Authorization: Bearer valid_token 헤더 필요)"
            },
            {
                "path": "/api/error-test",
                "description": "오류 핸들링 테스트 엔드포인트"
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
        "components": {
            "app": {"status": "UP"}
        }
    }
    
    # DB 상태 확인 예시
    # try:
    #     await app.state.db.ping()
    #     status["components"]["database"] = {"status": "UP"}
    # except Exception as e:
    #     status["status"] = "DOWN"
    #     status["components"]["database"] = {
    #         "status": "DOWN", 
    #         "error": str(e)
    #     }
    
    return status

# 메인 실행 함수 (애플리케이션 직접 실행 시)
if __name__ == "__main__":
    """
    메인 실행 함수
    - 직접 실행 시 Uvicorn ASGI 서버 시작
    - FastAPI-Flow 프로젝트는 다음 세 가지 방식으로 실행 가능:
    
    1. Python 모듈로 직접 실행:
       $ python -m app.main
    
    2. Uvicorn으로 실행 (개발):
       $ uvicorn app.main:app --reload
    
    3. Gunicorn + UvicornWorker로 실행 (프로덕션):
       $ gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4
    """
    import uvicorn
    
    # 환경 변수에서 설정 로드 (또는 기본값 사용)
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "True").lower() in ("true", "1", "t")
    log_level = os.getenv("LOG_LEVEL", "info")
    
    logger.info(f"🚀 Uvicorn ASGI 서버 시작 중... (host={host}, port={port}, reload={reload})")
    
    # Uvicorn 서버 설정 및 시작
    uvicorn.run(
        "app.main:app",  # 애플리케이션 임포트 경로
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )