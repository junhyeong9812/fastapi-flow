from fastapi import Request
import time
import logging
from typing import Callable

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def logging_middleware(request: Request, call_next: Callable):
    """
    ✅ HTTP 요청 로깅 미들웨어
    - Spring의 Filter와 대응되는 개념
    - 모든 HTTP 요청에 대해 실행되며 요청 전/후 처리를 담당
    - 요청 처리 전후에 로깅을 수행하고 처리 시간을 측정
    
    🔍 주요 특징:
    - FastAPI의 미들웨어는 async 함수로 구현 (Spring Filter는 동기식)
    - call_next를 통해 다음 미들웨어나 라우터로 요청을 전달 (Spring의 filterChain.doFilter와 유사)
    - request 객체에 커스텀 속성 추가 가능 (request.state 활용)
    
    🔧 추가 가능 설정:
    - 특정 경로만 로깅: path에 따른 조건 추가
    - 요청 본문 로깅: await request.body() 사용 (주의: 스트림 소비됨)
    - 응답 데이터 로깅: Response 객체 래핑 필요
    """
    # 요청 시작 시간 기록
    start_time = time.time()
    
    # 요청 정보 로깅
    path = request.url.path
    method = request.method
    client_host = request.client.host if request.client else "Unknown"
    
    logger.info(f"[LoggingMiddleware] ▶️ 요청: [{method}] {path} from {client_host}")
    
    # 고유 요청 ID 생성 및 저장 (MDC와 유사)
    # import uuid
    # request_id = str(uuid.uuid4())
    # request.state.request_id = request_id
    # logger.info(f"[{request_id}] 요청 시작: {path}")
    
    try:
        # 다음 미들웨어 또는 라우터로 요청 전달 (Spring의 filterChain.doFilter와 유사)
        response = await call_next(request)
        
        # 처리 시간 계산
        process_time = time.time() - start_time
        
        # 응답 정보 로깅
        status_code = response.status_code
        logger.info(f"[LoggingMiddleware] ⏹️ 응답 완료: [{method}] {path} - {status_code} - {process_time:.4f}초")
        
        # 응답 본문 로깅 예시 (비활성화 상태)
        # response_body = b""
        # async for chunk in response.body_iterator:
        #     response_body += chunk
        # logger.debug(f"응답 본문: {response_body.decode()}")
        # 
        # # 원본 응답 대체 (StreamingResponse로 래핑)
        # return StreamingResponse(
        #     iter([response_body]),
        #     status_code=response.status_code,
        #     headers=dict(response.headers),
        #     media_type=response.media_type
        # )
        
        # 일반적인 경우 원본 응답 반환
        return response
    
    except Exception as e:
        # 예외 발생 시 로깅
        process_time = time.time() - start_time
        logger.error(f"[LoggingMiddleware] ❌ 예외 발생: [{method}] {path} - {str(e)} - {process_time:.4f}초")
        # 예외를 다시 발생시켜 글로벌 예외 핸들러가 처리하도록 함
        raise
    
    """
    🔍 추가 활용 옵션:
    
    1. 요청 압축 해제 미들웨어:
    
    async def compression_middleware(request: Request, call_next):
        body = await request.body()
        if request.headers.get("Content-Encoding") == "gzip":
            import gzip
            body = gzip.decompress(body)
            # 요청 객체 재생성 (FastAPI에서는 불가능하므로 커스텀 속성으로 저장)
            request.state.decompressed_body = body
        
        return await call_next(request)
    
    2. CORS 미들웨어 (FastAPI에서는 CORSMiddleware 제공):
    
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080", "https://example.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    3. 인증 미들웨어:
    
    async def auth_middleware(request: Request, call_next):
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "인증이 필요합니다."}
            )
        
        try:
            # JWT 토큰 검증 예시 
            # from jose import jwt
            # payload = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM])
            # request.state.user_id = payload.get("sub")
            pass
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "유효하지 않은 인증 토큰입니다."}
            )
        
        return await call_next(request)
    
    4. 응답 래핑 미들웨어:
    
    async def response_wrapper_middleware(request: Request, call_next):
        response = await call_next(request)
        
        # JSON 응답인 경우에만 래핑
        if response.headers.get("content-type") == "application/json":
            # 원본 응답 본문 가져오기
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # 응답 본문 파싱
            import json
            data = json.loads(body)
            
            # 래핑된 응답 생성
            wrapped_data = {
                "success": response.status_code < 400,
                "data": data,
                "timestamp": time.time()
            }
            
            # 새 JSONResponse 반환
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content=wrapped_data,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        
        return response
    
    5. 성능 측정 미들웨어:
    
    async def performance_middleware(request: Request, call_next):
        import time
        import psutil
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        response = await call_next(request)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        logger.info(f"성능: 경로={request.url.path} "
                    f"시간={end_time - start_time:.4f}초 "
                    f"메모리증가={end_memory - start_memory:.2f}MB")
        
        return response
    
    🔧 흐름 테스트 방법:
    
    1. 미들웨어 체인 동작 검증:
    - 여러 미들웨어를 등록하고 로그를 통해 실행 순서 확인
    - FastAPI에서는 마지막에 추가된 미들웨어가 가장 먼저 실행됨 (Spring Filter와 반대)
    - app.middleware("http")(middleware3)
    - app.middleware("http")(middleware2)
    - app.middleware("http")(middleware1)
    - 위 경우 실행 순서: middleware1 -> middleware2 -> middleware3 -> 라우터 -> middleware3 -> middleware2 -> middleware1
    
    2. 미들웨어 선택적 적용:
    - 경로 기반 조건을 통해 특정 요청에만 미들웨어 적용
    - if request.url.path.startswith("/api"):
    -     # API 요청에만 로직 적용
    
    3. 미들웨어 오버헤드 분석:
    - 각 미들웨어의 처리 시간을 개별적으로 측정하여 성능 병목 식별
    """