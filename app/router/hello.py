from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Annotated, List
import logging
from pydantic import BaseModel
from app.dependency.auth import auth_required, get_current_user, with_logging
from app.exception.global_handler import AppException

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api", tags=["hello"])

"""
✅ 라우터 구현
- Spring의 @RestController에 대응되는 개념
- API 엔드포인트 정의 및 요청 처리 로직 구현
- 경로 매개변수, 쿼리 매개변수, 요청 본문 처리

🔍 주요 특징:
- FastAPI의 APIRouter 사용 (Spring의 @RequestMapping 유사)
- 경로 접두사 및 태그 설정으로 API 그룹화
- 의존성 주입(Depends)으로 공통 로직 분리 (Spring의 인터셉터와 유사)
- 응답 모델 및 상태 코드 명시적 지정 가능
"""

@router.get("/hello")
async def hello() -> Dict[str, str]:
    """
    기본 Hello 엔드포인트
    - 간단한 문자열 메시지 반환
    - Spring의 @GetMapping("/hello") 메서드와 유사
    """
    logger.info("[HelloController] hello() 메서드 실행")
    return {"message": "Hello, FastAPI-Flow!"}


@router.get("/hello/{name}")
async def hello_name(name: str) -> Dict[str, str]:
    """
    경로 매개변수를 활용한 Hello 엔드포인트
    - URL 경로에서 추출한 이름을 응답에 포함
    - Spring의 @PathVariable과 유사
    """
    logger.info(f"[HelloController] hello_name() 메서드 실행, name={name}")
    return {"message": f"Hello, {name}!"}


@router.get("/hello-query")
async def hello_query(name: str = "World") -> Dict[str, str]:
    """
    쿼리 매개변수를 활용한 Hello 엔드포인트
    - URL 쿼리 문자열에서 추출한 이름을 응답에 포함
    - 기본값 제공 가능
    - Spring의 @RequestParam과 유사
    """
    logger.info(f"[HelloController] hello_query() 메서드 실행, name={name}")
    return {"message": f"Hello, {name} from query!"}


@router.get("/hello-auth")
async def hello_auth(
    # auth_required 의존성 주입 (Spring의 @PreAuthorize와 유사)
    _: Annotated[None, Depends(auth_required)],
    # 현재 인증된 사용자 정보 주입 (Spring의 @AuthenticationPrincipal과 유사)
    user: Annotated[Dict[str, Any], Depends(get_current_user)]
) -> Dict[str, Any]:
    """
    인증이 필요한 Hello 엔드포인트
    - auth_required 의존성을 통한 인증 확인
    - 인증된 사용자 정보 포함한 응답 반환
    """
    logger.info(f"[HelloController] hello_auth() 메서드 실행, user_id={user['id']}")
    return {
        "message": f"Hello, {user['username']}!",
        "user_id": user["id"],
        "role": user["role"]
    }


# with_logging 데코레이터 적용 (Spring의 @LogExecutionTime과 유사)
@router.get("/error-test")
@with_logging
async def error_test() -> Dict[str, str]:
    """
    오류 테스트 엔드포인트
    - 의도적으로 예외 발생시켜 글로벌 예외 핸들러 테스트
    - Spring의 예외 처리 흐름 테스트와 동일한 목적
    """
    logger.info("[HelloController] error_test() 메서드 실행")
    # 의도적인 예외 발생
    raise AppException(
        status_code=500,
        message="테스트 예외 발생",
        error_code="TEST_ERROR"
    )


# 요청 본문을 받는 엔드포인트 예시
class HelloRequest(BaseModel):
    """
    Hello 요청 모델
    - Spring의 @RequestBody DTO와 유사
    - Pydantic 모델을 통한 자동 유효성 검사
    """
    name: str
    message: str
    tags: List[str] = []


@router.post("/hello")
async def hello_post(request: HelloRequest) -> Dict[str, Any]:
    """
    POST 요청을 처리하는 Hello 엔드포인트
    - JSON 요청 본문을 HelloRequest 모델로 변환
    - Spring의 @RequestBody와 유사
    """
    logger.info(f"[HelloController] hello_post() 메서드 실행, request={request}")
    return {
        "message": f"Hello, {request.name}!",
        "your_message": request.message,
        "tags": request.tags,
        "tag_count": len(request.tags)
    }


# 상태 코드 지정 예시
from fastapi import status
from fastapi.responses import JSONResponse

@router.post("/hello-created", status_code=status.HTTP_201_CREATED)
async def hello_created(request: HelloRequest) -> Dict[str, Any]:
    """
    생성 성공 상태 코드(201)를 반환하는 엔드포인트
    - status_code를 통한 응답 상태 코드 명시
    - Spring의 @ResponseStatus와 유사
    """
    logger.info(f"[HelloController] hello_created() 메서드 실행, request={request}")
    return {
        "id": "12345",  # 가상의 생성된 리소스 ID
        "name": request.name,
        "message": request.message,
        "created_at": datetime.datetime.now().isoformat()
    }


# 커스텀 응답 반환 예시
@router.get("/hello-custom")
async def hello_custom() -> JSONResponse:
    """
    커스텀 응답 형식을 사용하는 엔드포인트
    - JSONResponse를 직접 반환
    - 응답 헤더, 쿠키 등 추가 설정 가능
    """
    logger.info("[HelloController] hello_custom() 메서드 실행")
    
    # 커스텀 응답 생성
    response = JSONResponse(
        content={"message": "Hello, custom response!"},
        status_code=200,
        headers={"X-Custom-Header": "Custom Value"}
    )
    
    # 쿠키 설정
    response.set_cookie(
        key="session",
        value="example",
        max_age=3600,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return response

"""
🔍 추가 활용 옵션:

1. 응답 모델 사용 (Response Model):

class HelloResponse(BaseModel):
    message: str
    timestamp: str
    version: str = "1.0"

@router.get("/hello-model", response_model=HelloResponse)
async def hello_model():
    return {
        "message": "Hello with response model!",
        "timestamp": datetime.datetime.now().isoformat(),
        "extra_field": "이 필드는 응답에서 필터링됨"  # response_model로 인해 제외됨
    }

2. 의존성 라우터 수준 적용:

secure_router = APIRouter(
    prefix="/secure",
    tags=["secure"],
    dependencies=[Depends(auth_required)]  # 이 라우터의 모든 엔드포인트에 인증 필요
)

@secure_router.get("/data")
async def get_secure_data():
    return {"data": "This is secure data"}

3. 여러 HTTP 메서드 지원:

@router.api_route("/resource", methods=["GET", "POST", "PUT", "DELETE"])
async def resource(request: Request):
    method = request.method
    if method == "GET":
        return {"message": "Resource retrieved"}
    elif method == "POST":
        return {"message": "Resource created"}
    elif method == "PUT":
        return {"message": "Resource updated"}
    elif method == "DELETE":
        return {"message": "Resource deleted"}

4. 파일 업로드 처리:

from fastapi import File, UploadFile

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    
    # 파일 정보 로깅
    logger.info(f"파일 업로드: {file.filename}, 크기: {len(contents)} 바이트")
    
    # 파일 저장 예시
    # with open(f"uploads/{file.filename}", "wb") as f:
    #     f.write(contents)
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents)
    }

5. WebSocket 엔드포인트:

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"WebSocket 메시지 수신: {data}")
            await websocket.send_text(f"메시지 수신 확인: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket 연결 종료")

🔧 흐름 테스트 방법:

1. 다양한 요청 메서드 테스트:
- curl 또는 Postman 등 API 테스트 도구를 사용하여 엔드포인트 호출
- GET, POST, PUT, DELETE 메서드 테스트 
- 인증이 필요한 엔드포인트에 토큰 없이 요청하여 401 응답 확인

2. 경로 및 쿼리 매개변수 검증:
- /api/hello/{name} 경로에 다양한 값 전달 테스트
- 쿼리 매개변수 유무에 따른 기본값 동작 확인

3. 유효성 검사 테스트:
- HelloRequest 모델에 맞지 않는 요청 본문 전송하여 400 오류 확인
- 필수 필드 누락, 타입 불일치 등 다양한 유효성 검사 시나리오 테스트
"""