from fastapi import Request, Depends, HTTPException
from typing import Optional, Callable, TypeVar, Annotated
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 제네릭 타입 변수 정의 (Callable의 반환 타입)
T = TypeVar('T')

def auth_required(request: Request) -> None:
    """
    ✅ 인증 의존성 (Dependency)
    - Spring의 HandlerInterceptor.preHandle과 대응되는 개념
    - 특정 라우트 핸들러 실행 전에 호출되어 인증 여부 검사
    - 인증되지 않은 요청은 HTTP 401 예외 발생
    
    🔍 주요 특징:
    - FastAPI의 Depends를 통해 라우터에 주입 (Spring의 인터셉터와 유사)
    - Spring과 달리 특정 라우터에만 선택적으로 적용 가능
    - 경로 패턴이 아닌 라우터 함수 단위로 적용
    
    🔧 사용 방법:
    - @app.get("/protected", dependencies=[Depends(auth_required)])
    - 또는 함수 매개변수로: def endpoint(auth: Annotated[None, Depends(auth_required)]): ...
    """
    # 요청 헤더에서 Authorization 토큰 추출
    auth_header = request.headers.get("Authorization")
    
    logger.info(f"[AuthDependency] ▶️ 인증 검사: {request.method} {request.url.path}")
    
    # 간단한 인증 검사 로직 (실제로는 JWT 검증 등 구현)
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning(f"[AuthDependency] ❌ 인증 실패: Authorization 헤더 없음")
        raise HTTPException(
            status_code=401,
            detail="인증이 필요합니다."
        )
    
    # 토큰 추출 (Bearer 제거)
    token = auth_header.replace("Bearer ", "")
    
    # 토큰 검증 로직 (실제로는 JWT 디코딩 및 검증)
    if token != "valid_token":  # 예시 값
        logger.warning(f"[AuthDependency] ❌ 인증 실패: 유효하지 않은 토큰")
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 인증 토큰입니다."
        )
    
    # 인증 성공 시 로그
    logger.info(f"[AuthDependency] ✅ 인증 성공")
    
    # 인증된 사용자 정보를 request.state에 저장 (선택 사항)
    # request.state.user_id = "user_123"
    
    # 의존성은 명시적 반환 값이 없어도 됨


def get_current_user(request: Request) -> dict:
    """
    인증된 사용자 정보 반환 의존성
    - Spring의 @AuthenticationPrincipal과 유사한 역할
    - 컨트롤러에서 현재 인증된 사용자 정보를 쉽게 접근 가능
    """
    # 인증 로직 (auth_required와 중복될 수 있으므로 실제로는 캐싱 고려)
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    # 사용자 정보 반환 (실제로는 JWT에서 추출하거나 DB 조회)
    return {
        "id": "user_123",
        "username": "example_user",
        "role": "admin"
    }


def admin_required(request: Request) -> None:
    """
    관리자 권한 검사 의존성
    - Spring의 @PreAuthorize("hasRole('ADMIN')")과 유사한 역할
    """
    # 먼저 인증 검사
    auth_required(request)
    
    # 사용자 정보 가져오기 (실제로는 JWT에서 추출하거나 DB 조회)
    user = get_current_user(request)
    
    # 관리자 권한 검사
    if user.get("role") != "admin":
        logger.warning(f"[AdminDependency] ❌ 권한 부족: 관리자만 접근 가능")
        raise HTTPException(
            status_code=403,
            detail="관리자 권한이 필요합니다."
        )
    
    logger.info(f"[AdminDependency] ✅ 관리자 권한 확인됨")


def log_request(request: Request) -> None:
    """
    요청 로깅 의존성
    - Spring의 @LogExecutionTime 같은 AOP 어노테이션과 유사한 역할
    """
    method = request.method
    path = request.url.path
    client_host = request.client.host if request.client else "Unknown"
    
    logger.info(f"[LogRequestDependency] 요청 정보: [{method}] {path} from {client_host}")


def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """
    속도 제한 의존성 팩토리
    - Spring의 @RateLimiter와 유사한 역할
    - 매개변수화된 의존성 생성을 위한 클로저 패턴
    """
    def rate_limit_dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "Unknown"
        
        # 실제로는 Redis 등을 사용한 카운터 구현
        # 현재는 간단한 로그만 출력
        logger.info(f"[RateLimitDependency] IP {client_ip}에 대한 속도 제한 검사 "
                    f"(최대 {max_requests}회/{window_seconds}초)")
        
        # 실제 구현 예시
        # import redis
        # r = redis.Redis()
        # key = f"rate_limit:{client_ip}"
        # current = r.incr(key)
        # if current == 1:
        #     r.expire(key, window_seconds)
        # if current > max_requests:
        #     raise HTTPException(status_code=429, detail="너무 많은 요청이 발생했습니다.")
    
    return rate_limit_dependency


def with_logging(func: Callable[..., T]) -> Callable[..., T]:
    """
    함수 실행 로깅 데코레이터
    - Spring의 @Around 어드바이스와 유사
    - 함수 실행 전후에 로깅 수행
    """
    import functools
    import time
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        function_name = func.__name__
        logger.info(f"[LoggingDecorator] ▶️ 함수 실행 시작: {function_name}")
        
        start_time = time.time()
        try:
            # 함수 실행
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"[LoggingDecorator] ❌ 함수 실행 중 예외: {function_name} - {str(e)}")
            raise
        finally:
            execution_time = time.time() - start_time
            logger.info(f"[LoggingDecorator] ⏹️ 함수 실행 완료: {function_name} - {execution_time:.4f}초")
    
    return wrapper

"""
🔍 추가 활용 옵션:

1. 캐싱 의존성 (Spring의 @Cacheable과 유사):

def cached(cache_key: str, ttl_seconds: int = 3600):
    def cache_dependency(request: Request) -> dict:
        # 실제로는 Redis 등의 캐시 사용
        # 간단한 예시로 메모리 캐시 사용
        import functools
        cache = getattr(cached, 'cache', {})
        cached.cache = cache
        
        if cache_key in cache:
            logger.info(f"캐시 히트: {cache_key}")
            return cache[cache_key]
        
        # 실제 데이터 로드 로직
        data = {"sample": "data"}  # 실제로는 DB 조회 등
        
        # 캐시에 저장
        cache[cache_key] = data
        logger.info(f"캐시 저장: {cache_key}")
        
        # TTL 설정 (실제로는 Redis의 EXPIRE 등 사용)
        # 여기서는 생략
        
        return data
    return cache_dependency

2. 트랜잭션 의존성 (Spring의 @Transactional과 유사):

def transactional(db_session):
    def transaction_dependency():
        try:
            # 트랜잭션 시작
            logger.info("트랜잭션 시작")
            yield
            # 트랜잭션 커밋
            db_session.commit()
            logger.info("트랜잭션 커밋")
        except Exception as e:
            # 트랜잭션 롤백
            db_session.rollback()
            logger.error(f"트랜잭션 롤백: {str(e)}")
            raise
    return Depends(transaction_dependency)

3. 요청 컨텍스트 의존성 (Spring의 RequestContextHolder와 유사):

class RequestContext:
    def __init__(self, request: Request):
        self.request = request
        self.start_time = time.time()
        self.attributes = {}
    
    def set_attribute(self, name: str, value: any) -> None:
        self.attributes[name] = value
    
    def get_attribute(self, name: str, default=None) -> any:
        return self.attributes.get(name, default)
    
    def get_execution_time(self) -> float:
        return time.time() - self.start_time

def get_request_context(request: Request) -> RequestContext:
    # request.state를 활용하여 컨텍스트 저장
    if not hasattr(request.state, "context"):
        request.state.context = RequestContext(request)
    return request.state.context

4. 파라미터 유효성 검사 의존성:

def validate_parameters(min_value: int = 0, max_value: int = 100):
    def validate(value: int = Query(..., description="검증이 필요한 값")):
        if value < min_value or value > max_value:
            raise HTTPException(
                status_code=400,
                detail=f"값은 {min_value}에서 {max_value} 사이여야 합니다."
            )
        return value
    return Depends(validate)

5. 사용자 지정 로그 레벨 의존성:

def with_log_level(level: int):
    def log_level_dependency():
        original_level = logger.level
        logger.setLevel(level)
        yield
        logger.setLevel(original_level)
    return Depends(log_level_dependency)

🔧 흐름 테스트 방법:

1. 다양한 의존성 조합 테스트:
- 여러 의존성을 다양한 순서로 적용하고 로그로 실행 순서 확인
- @app.get("/test", dependencies=[Depends(auth_required), Depends(log_request)])
- 또는 개별 매개변수로 주입: 
  def endpoint(
      _auth: Annotated[None, Depends(auth_required)],
      _log: Annotated[None, Depends(log_request)],
      user: Annotated[dict, Depends(get_current_user)]
  ): ...

2. 전역 의존성 vs 핸들러별 의존성 비교:
- app = FastAPI(dependencies=[Depends(log_request)])  # 전역 의존성
- @app.get("/specific", dependencies=[Depends(auth_required)])  # 핸들러별 의존성

3. 의존성 오버헤드 분석:
- 복잡한 의존성 그래프에서의 성능 측정
- 중복 의존성 호출 방지 (use_cache=True가 기본값)
- 의존성 깊이와 실행 순서 파악
"""