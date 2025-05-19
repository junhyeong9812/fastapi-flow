from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Any, Dict, Union
import logging
from datetime import datetime
import traceback

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppException(Exception):
    """
    애플리케이션 내부에서 사용하는 커스텀 예외 클래스
    - Spring의 ResponseStatusException과 유사한 역할
    """
    def __init__(
        self, 
        status_code: int, 
        message: str, 
        error_code: str = None, 
        details: Dict[str, Any] = None
    ):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    """
    ✅ 글로벌 예외 핸들러 등록
    - Spring의 @ControllerAdvice + @ExceptionHandler와 대응되는 개념
    - 애플리케이션 전체에서 발생하는 예외를 공통 포맷으로 처리
    - 다양한 예외 유형에 대한 개별 핸들러 등록
    
    🔍 주요 특징:
    - FastAPI의 exception_handler 데코레이터를 사용
    - Spring의 @ControllerAdvice처럼 전역 예외 처리 통합
    - HTTP 상태 코드와 표준화된 오류 응답 포맷 제공
    
    🔧 주요 예외 유형:
    - RequestValidationError: 요청 유효성 검사 실패 (400)
    - AppException: 애플리케이션 내부 커스텀 예외
    - Exception: 기타 모든 예외 처리 (500)
    """
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """
        요청 유효성 검사 예외 핸들러
        - Pydantic 모델 검증 실패 시 호출
        - Spring의 MethodArgumentNotValidException 핸들러와 유사
        """
        logger.warning(f"[ExceptionHandler] ⚠️ 유효성 검사 예외: {str(exc)}")
        
        # 오류 세부 정보 추출
        errors = []
        for error in exc.errors():
            error_detail = {
                "location": error["loc"],
                "message": error["msg"],
                "type": error["type"]
            }
            errors.append(error_detail)
        
        # 표준화된 오류 응답 생성
        return JSONResponse(
            status_code=400,
            content={
                "timestamp": datetime.now().isoformat(),
                "status": 400,
                "error": "Bad Request",
                "message": "요청 데이터 유효성 검사 실패",
                "path": request.url.path,
                "details": errors
            }
        )
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """
        애플리케이션 커스텀 예외 핸들러
        - 비즈니스 로직에서 발생시킨 예외 처리
        - Spring의 @ResponseStatus 또는 ResponseStatusException과 유사
        """
        logger.warning(f"[ExceptionHandler] ⚠️ 애플리케이션 예외: {exc.message}, 코드: {exc.status_code}")
        
        # 커스텀 예외 응답 생성
        response_content = {
            "timestamp": datetime.now().isoformat(),
            "status": exc.status_code,
            "error": get_http_error_name(exc.status_code),
            "message": exc.message,
            "path": request.url.path
        }
        
        # 추가 상세 정보가 있으면 포함
        if exc.error_code:
            response_content["error_code"] = exc.error_code
            
        if exc.details:
            response_content["details"] = exc.details
        
        return JSONResponse(
            status_code=exc.status_code,
            content=response_content
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        일반 예외 핸들러 (폴백)
        - 다른 핸들러에서 처리되지 않은 모든 예외 처리
        - Spring의 @ExceptionHandler(Exception.class)와 유사
        """
        # 예외 정보 로깅 (스택 트레이스 포함)
        logger.error(f"[ExceptionHandler] ❌ 처리되지 않은 예외: {str(exc)}")
        logger.error(traceback.format_exc())
        
        # 500 Internal Server Error 응답
        return JSONResponse(
            status_code=500,
            content={
                "timestamp": datetime.now().isoformat(),
                "status": 500,
                "error": "Internal Server Error",
                "message": "서버 내부 오류가 발생했습니다",
                "path": request.url.path
                # 주의: 프로덕션 환경에서는 실제 오류 메시지 노출 금지
                # "detail": str(exc) if app.debug else None
            }
        )


def get_http_error_name(status_code: int) -> str:
    """HTTP 상태 코드에 해당하는 표준 오류 이름 반환"""
    http_status_codes = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout"
    }
    return http_status_codes.get(status_code, "Unknown Error")

"""
🔍 추가 활용 옵션:

1. 도메인별 예외 처리:

class UserException(AppException):
    def __init__(self, status_code: int, message: str, user_id: str = None):
        details = {"user_id": user_id} if user_id else None
        super().__init__(status_code, message, "USER_ERROR", details)

class ProductException(AppException):
    def __init__(self, status_code: int, message: str, product_id: str = None):
        details = {"product_id": product_id} if product_id else None
        super().__init__(status_code, message, "PRODUCT_ERROR", details)

# 핸들러 등록
@app.exception_handler(UserException)
async def user_exception_handler(request: Request, exc: UserException):
    # 사용자 관련 예외 특화 처리
    logger.error(f"사용자 오류: {exc.message}, 사용자 ID: {exc.details.get('user_id')}")
    return JSONResponse(...)

2. 환경별 예외 응답 차별화:

def configure_exception_handling(app: FastAPI, env: str):
    @app.exception_handler(Exception)
    async def env_aware_exception_handler(request: Request, exc: Exception):
        # 개발 환경에서는 상세 오류 정보 제공
        if env == "development":
            return JSONResponse(
                status_code=500,
                content={
                    "message": str(exc),
                    "traceback": traceback.format_exc().splitlines()
                }
            )
        
        # 프로덕션 환경에서는 최소한의 정보만 제공
        elif env == "production":
            # 오류는 로그에만 기록
            logger.error(f"오류: {str(exc)}")
            logger.error(traceback.format_exc())
            
            return JSONResponse(
                status_code=500,
                content={"message": "서버 오류가 발생했습니다"}
            )

3. 오류 응답 프로토콜 확장:

class APIError:
    def __init__(self, status_code: int, message: str, error_code: str = None, details: dict = None):
        self.status_code = status_code
        self.content = {
            "timestamp": datetime.now().isoformat(),
            "status": status_code,
            "error": get_http_error_name(status_code),
            "message": message,
            "error_code": error_code,
            "details": details
        }
        
        # None 값 제거
        self.content = {k: v for k, v in self.content.items() if v is not None}
    
    def to_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content=self.content
        )

# 사용 예시:
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return APIError(
        status_code=400,
        message="유효성 검사 실패",
        error_code="VALIDATION_ERROR",
        details={"fields": exc.errors()}
    ).to_response()

4. 에러 코드 체계 구축:

class ErrorCodes:
    # 인증 관련 오류 (401, 403)
    AUTH_INVALID_TOKEN = "AUTH001"
    AUTH_EXPIRED_TOKEN = "AUTH002"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH003"
    
    # 리소스 오류 (404, 409)
    RESOURCE_NOT_FOUND = "RES001"
    RESOURCE_ALREADY_EXISTS = "RES002"
    RESOURCE_STATE_CONFLICT = "RES003"
    
    # 유효성 검사 오류 (400)
    VALIDATION_INVALID_FORMAT = "VAL001"
    VALIDATION_REQUIRED_FIELD = "VAL002"
    VALIDATION_OUT_OF_RANGE = "VAL003"
    
    # 서버 오류 (500)
    SERVER_DATABASE_ERROR = "SRV001"
    SERVER_EXTERNAL_SERVICE_ERROR = "SRV002"
    SERVER_UNEXPECTED_ERROR = "SRV999"

# 사용 예시:
raise AppException(
    status_code=404,
    message="요청한 사용자를 찾을 수 없습니다",
    error_code=ErrorCodes.RESOURCE_NOT_FOUND,
    details={"user_id": "123"}
)

5. 예외 로깅 미들웨어:

class ExceptionLoggingMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            # 스코프에서 요청 정보 추출
            path = scope.get("path", "Unknown")
            method = scope.get("method", "Unknown")
            
            # 오류 로깅
            logger.error(f"미들웨어에서 처리되지 않은 예외: {method} {path} - {str(e)}")
            logger.error(traceback.format_exc())
            
            # 예외 다시 발생
            raise

🔧 흐름 테스트 방법:

1. 다양한 예외 발생 시나리오 테스트:
- 유효하지 않은 요청 본문 전송으로 RequestValidationError 유발
- 비즈니스 로직에서 AppException 발생
- 예상치 못한 서버 오류 발생 (예: 데이터베이스 연결 실패)

2. 환경별 예외 처리 동작 확인:
- 개발 환경: 상세 오류 정보 및 스택 트레이스 제공
- 프로덕션 환경: 사용자 친화적인 메시지만 제공, 상세 정보는 로그에만 기록

3. 로깅 검증:
- 각 예외 유형별 로그 레벨 및 포맷 확인
- 중요 정보(예: 사용자 식별자)가 로그에 포함되는지 확인
"""