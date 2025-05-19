# FastAPI-Flow

## 📌 프로젝트 개요

**FastAPI-Flow**는 Python 기반의 FastAPI 프레임워크를 활용하여, 실제 FastAPI 내부의 요청 처리 흐름과 미들웨어 동작, 예외 처리, 라우팅, AOP 유사 기능 등을 **Spring MVC 구조에 대응하는 방식으로 직접 구성하고 실험**하는 학습용 프로젝트입니다.

이 프로젝트는 FastAPI의 자동 동작 원리를 직접 구성함으로써, 프레임워크의 내부 구조를 더 깊이 이해하고 실무에서의 판단력을 높이는 것을 목표로 합니다.

---

## 📝 Python 서버 환경 설명 (Flask, FastAPI, Uvicorn, Gunicorn)

### 톰캣과 파이썬 서버 비교

| 구조      | Spring MVC                 | FastAPI                | Flask                             |
| ------- | -------------------------- | ---------------------- | --------------------------------- |
| 서버 구조   | Tomcat (Servlet container) | Uvicorn (ASGI)         | Gunicorn (WSGI) or Waitress       |
| 프레임워크   | Spring                     | FastAPI                | Flask                             |
| 시작 프로세스 | `SpringApplication.run()`  | `uvicorn main:app`     | `flask run` or `gunicorn app:app` |
| 처리 방식   | Thread 기반 방식              | AsyncIO (non-blocking) | Blocking (멀티 프로세스로 보완)             |

### WSGI vs ASGI 인터페이스

| 항목         | **WSGI (Web Server Gateway Interface)** | **ASGI (Asynchronous Server Gateway Interface)** |
| ---------- | --------------------------------------- | ----------------------------------------------- |
| 처리 모델       | 동기식 (요청 당 하나의 스레드/프로세스)                 | 비동기식 (이벤트 루프 기반)                               |
| 동시성        | 제한적 (멀티스레드/멀티프로세싱)                     | 높음 (코루틴 기반)                                     |
| 실시간 기능     | 제한적 (롱폴링 등 우회 필요)                       | 기본 지원 (WebSocket, SSE 등)                        |
| 대표 프레임워크   | Flask, Django (기본 모드)                    | FastAPI, Starlette, Django (ASGI 모드)            |
| 대표 서버      | Gunicorn, uWSGI                          | Uvicorn, Daphne, Hypercorn                      |
| I/O 효율성    | 낮음 (블로킹 I/O)                            | 높음 (논블로킹 I/O)                                  |
| 메모리 효율성    | 낮음 (프로세스/스레드 부하)                        | 높음 (적은 프로세스로 다수 요청 처리)                         |
| 코드 복잡성     | 낮음 (직관적 순차 코드)                          | 중간 (async/await 패턴 이해 필요)                       |
| 채택 시기      | 2003년 (PEP 333)                          | 2018년 (ASGI 명세)                                 |

### Uvicorn vs Gunicorn

| 항목         | **Uvicorn**                    | **Gunicorn**                            |
| ---------- | ------------------------------ | --------------------------------------- |
| 유형         | ASGI 서버 (비동기 지원)               | WSGI 서버 (동기 기반)                         |
| 비동기 지원     | O (FastAPI 최적화)                | X (기본), 단 `UvicornWorker`로 가능           |
| 멀티 프로세스 관리 | X (단일 프로세스 또는 --workers 수동 지정) | O (기본적으로 멀티 워커 운영)                      |
| 활용 예시      | FastAPI 개발용/소규모 운영             | Flask 운영용 or FastAPI + UvicornWorker 조합 |

### Gunicorn + UvicornWorker 조합 (FastAPI 실전 운영용)

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 4
```

* **Gunicorn**: 워커 프로세스 관리, 로깅, 프로세스 감시 담당
* **UvicornWorker**: 실제 FastAPI ASGI 요청 처리 담당
* **장점**: 비동기 처리 + 프로세스 안정성 둘 다 확보 가능

### 주요 차이점 요약

* **Flask**는 동기/WSGI 기반으로 단순 구조지만, 고성능 I/O에는 부적합
* **FastAPI**는 비동기/ASGI 구조로 고성능 비동기 처리를 효율적으로 수행
* **Uvicorn**은 FastAPI 실행용 ASGI 서버
* **Gunicorn**은 프로세스 관리용 → UvicornWorker와 조합하여 FastAPI 운영 시 실전 배포 구성 가능

---

## 🌟 학습 목표

- ASGI 기반 요청 처리 흐름 구조 파악 (Uvicorn → Middleware → Dependency → Router → Handler)
- Spring MVC의 DispatcherServlet, Filter, Interceptor, Controller 환경과 1:1 매핑 개념 실습
- FastAPI의 미들웨어, 의존성 주입(Interceptor 유사), 전역 예외 처리, 데코레이터 기능 실험
- 모든 흐름을 로그와 구조화된 문서로 추적 가능하게 구성
- RESTful API 응답 처리 + (선택) HTML 렌더링(Jinja2) 통합 실험

---

## ⚙️ 기술 스택

- Python 3.11+
- FastAPI 0.110.1
- Uvicorn 0.29.0 (ASGI 서버)
- (선택) Jinja2 템플릿
- (선택) aioredis / SQLAlchemy (특정 실험에서 사용)

---

## 🏠 프로젝트 구조

```
fastapi-flow/
├── app/
│   ├── main.py                      # FastAPI 진입점 (DispatcherServlet 역할)
│   ├── middleware/                  # Filter 대응
│   │   └── logging.py               # 로깅 미들웨어
│   ├── router/                      # Controller 대응
│   │   └── hello.py                 # 예제 라우터
│   ├── service/                     # Service 계층
│   │   └── example_service.py       # 예제 서비스
│   ├── exception/                   # 글로벌 예외 처리
│   │   └── global_handler.py        # 예외 핸들러
│   └── dependency/                  # Interceptor 대응
│       └── auth.py                  # 인증 의존성
├── requirements.txt                 # 의존성 목록
└── README.md                        # 프로젝트 문서
```

## 🔄 요청 처리 흐름

### FastAPI 요청 처리 단계별 흐름 (Spring MVC와 비교)

```
클라이언트 요청
   ↓
[Uvicorn ASGI 서버]              ← Tomcat/Jetty 서버
   ↓
[FastAPI 애플리케이션]            ← DispatcherServlet
   ↓
[Middleware (logging 등)]       ← Filter
   ↓
[Dependency (auth 등)]          ← HandlerInterceptor
   ↓
[Router → Handler 호출]         ← @Controller 메서드
   ↓
[Service 레이어]                 ← @Service
   ↓
[예외 발생 시 Exception Handler] ← @ControllerAdvice
```

### 상세 요청 처리 흐름 (예: `/api/hello` 엔드포인트)

1. **클라이언트**: GET /api/hello 요청 전송
2. **Uvicorn**: HTTP 요청 수신 및 ASGI 형식으로 변환
3. **FastAPI**: 요청 경로 매핑 및 해당 라우터 검색
4. **로깅 미들웨어**: 요청 정보 기록 (URL, 메서드, 클라이언트 IP 등)
5. **인증 의존성**: 필요시 인증 검증 수행 (해당 경로에 적용된 경우)
6. **로깅 데코레이터**: 핸들러 함수 실행 시간 측정 시작
7. **라우터 핸들러**: hello() 함수 실행
8. **서비스 계층**: 필요시 비즈니스 로직 실행
9. **응답 생성**: JSON 응답 생성 및 반환
10. **로깅 데코레이터**: 함수 실행 시간 측정 완료
11. **로깅 미들웨어**: 응답 상태 및 처리 시간 기록
12. **Uvicorn**: HTTP 응답 클라이언트에게 전송

### 예외 처리 흐름 (예: `/api/error-test` 엔드포인트)

1. **클라이언트**: GET /api/error-test 요청 전송
2. **미들웨어/의존성** 단계 통과
3. **라우터 핸들러**: 의도적으로 `AppException` 발생
4. **로깅 데코레이터**: 예외 감지 및 로깅
5. **글로벌 예외 핸들러**: `app_exception_handler` 함수가 예외 처리
6. **표준화된 오류 응답**: JSON 형식의 오류 응답 생성
7. **로깅 미들웨어**: 오류 응답 로깅
8. **클라이언트**: 표준화된 오류 응답 수신

## 🧩 주요 컴포넌트 설명

### 1) main.py - FastAPI 애플리케이션 (DispatcherServlet 대응)

* FastAPI 앱 설정 및 초기화
* 라이프사이클 이벤트 관리 (시작/종료 처리)
* 미들웨어, 라우터, 예외 핸들러 등록
* 기본 경로 및 상태 확인 엔드포인트 제공

```python
# FastAPI 앱 생성
app = FastAPI(
    title="FastAPI-Flow",
    description="Spring MVC 패턴을 FastAPI로 구현한 학습용 프로젝트",
    lifespan=lifespan  # 애플리케이션 라이프사이클 관리자
)

# 미들웨어 등록 (Filter)
app.middleware("http")(logging_middleware)

# 라우터 등록 (Controller)
app.include_router(hello_router)

# 예외 핸들러 등록 (@ControllerAdvice)
register_exception_handlers(app)
```

### 2) logging.py - 로깅 미들웨어 (Filter 대응)

* 모든 HTTP 요청/응답에 대한 로깅 처리
* 요청 처리 시간 측정
* 클라이언트 정보, URL, 상태 코드 등 기록

```python
@app.middleware("http")
async def logging_middleware(request: Request, call_next: Callable):
    # 요청 정보 로깅
    logger.info(f"[LoggingMiddleware] ▶️ 요청: [{request.method}] {request.url.path}")
    
    # 다음 미들웨어/핸들러로 요청 전달
    response = await call_next(request)
    
    # 응답 정보 로깅
    logger.info(f"[LoggingMiddleware] ⏹️ 응답 완료: 상태 코드 {response.status_code}")
    
    return response
```

### 3) auth.py - 인증 의존성 (HandlerInterceptor 대응)

* 특정 엔드포인트에 인증 요구사항 적용
* 토큰 검증 및 사용자 정보 추출
* 인증/권한 검사 실패 시 적절한 HTTP 오류 반환

```python
def auth_required(request: Request):
    # 인증 토큰 검사
    if "Authorization" not in request.headers:
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    
    # 실제 애플리케이션에서는 JWT 등 토큰 검증 로직 구현
```

### 4) hello.py - 라우터/핸들러 (Controller 대응)

* HTTP 엔드포인트 정의
* 요청 매개변수 처리 (경로, 쿼리, 본문)
* 응답 데이터 반환

```python
@router.get("/hello")
async def hello():
    logger.info("[HelloController] hello() 메서드 실행")
    return {"message": "Hello, FastAPI-Flow!"}

@router.get("/hello/{name}")
async def hello_name(name: str):
    logger.info(f"[HelloController] hello_name() 실행, name={name}")
    return {"message": f"Hello, {name}!"}
```

### 5) global_handler.py - 예외 핸들러 (@ControllerAdvice 대응)

* 애플리케이션 전체에 적용되는 예외 처리
* 예외 유형별 맞춤형 응답 생성
* 표준화된 오류 응답 포맷 제공

```python
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"[ExceptionHandler] 애플리케이션 예외: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "error": get_http_error_name(exc.status_code),
            "message": exc.message,
            "path": request.url.path
        }
    )
```

### 6) example_service.py - 서비스 레이어 (@Service 대응)

* 비즈니스 로직 구현
* 트랜잭션 처리 (데코레이터 활용)
* 도메인 객체 관리 및 예외 처리

```python
@transactional
async def create_item(item_data: Dict[str, Any]):
    logger.info(f"[ExampleService] 아이템 생성: {item_data}")
    
    # 비즈니스 로직 및 유효성 검사
    if "name" not in item_data:
        raise AppException(status_code=400, message="이름은 필수 항목입니다")
    
    # 데이터 저장 및 결과 반환
    return {"id": "123", "name": item_data["name"]}
```

## 📊 컴포넌트별 로그 출력 예시

### 정상 요청 시 로그

```
2023-07-21 14:30:00 - INFO - 🚀 애플리케이션 시작 - 리소스 초기화 중...
2023-07-21 14:30:00 - INFO - ✅ 애플리케이션 초기화 완료
2023-07-21 14:30:05 - INFO - [LoggingMiddleware] ▶️ 요청: [GET] /api/hello from 127.0.0.1
2023-07-21 14:30:05 - INFO - [HelloController] hello() 메서드 실행
2023-07-21 14:30:05 - INFO - [LoggingMiddleware] ⏹️ 응답 완료: [GET] /api/hello - 200 - 0.0123초
```

### 예외 발생 시 로그

```
2023-07-21 14:31:10 - INFO - [LoggingMiddleware] ▶️ 요청: [GET] /api/error-test from 127.0.0.1
2023-07-21 14:31:10 - INFO - [LoggingDecorator] ▶️ 함수 실행 시작: error_test
2023-07-21 14:31:10 - INFO - [HelloController] error_test() 메서드 실행
2023-07-21 14:31:10 - ERROR - [LoggingDecorator] ❌ 함수 실행 중 예외: error_test - 테스트 예외 발생
2023-07-21 14:31:10 - WARNING - [ExceptionHandler] ⚠️ 애플리케이션 예외: 테스트 예외 발생, 코드: 500
2023-07-21 14:31:10 - INFO - [LoggingMiddleware] ⏹️ 응답 완료: [GET] /api/error-test - 500 - 0.0345초
```

## 🔍 Spring MVC vs FastAPI 주요 차이점

### 1. 동기 vs 비동기 처리

**Spring MVC**:
- 기본적으로 동기식 처리 (스레드 당 하나의 요청 처리)
- WebFlux로 비동기 지원 가능하지만 별도 스택

**FastAPI**:
- 기본적으로 비동기식 처리 (`async/await`)
- 동시성 처리가 기본 내장 (ASGI 기반)
- I/O 작업에서 높은 성능 제공

### 2. 웹 서버 아키텍처

**Spring Boot + Tomcat**:
- 서블릿 컨테이너 기반 (WSGI와 유사)
- 스레드 풀 기반 멀티스레딩 모델
- 요청 당 스레드 할당

**FastAPI + Uvicorn**:
- ASGI 서버 (비동기 게이트웨이 인터페이스)
- 이벤트 루프 기반 비동기 처리
- 적은 수의 프로세스/스레드로 많은 동시 요청 처리 가능

### 3. 미들웨어 vs 필터 실행 순서

**Spring**:
- 필터 체인: 등록된 순서대로 전처리 → 후처리 역순 실행
  (Filter1 → Filter2 → ... → Controller → ... → Filter2 → Filter1)

**FastAPI**:
- 미들웨어: 마지막에 등록된 미들웨어가 먼저 실행되고, 응답은 등록 순서대로 처리
  (Middleware2 → Middleware1 → Router → Middleware1 → Middleware2)

### 4. 의존성 주입 방식

**Spring**:
- 컴파일 시점 또는 애플리케이션 시작 시 의존성 주입
- 컴포넌트 스캔과 빈 컨테이너 사용
- `@Autowired`, 생성자 주입 등 다양한 방식

**FastAPI**:
- 요청 시점에 의존성 주입 (`Depends`)
- 라우트 핸들러 매개변수로 의존성 주입
- 의존성 그래프 자동 해결

### 5. 타입 시스템과 검증

**Spring**:
- Java 클래스 기반 타입 시스템
- Bean Validation (`@Valid`, `@NotNull` 등)

**FastAPI**:
- Python 타입 힌팅 + Pydantic 모델
- 자동 요청 검증 및 OpenAPI 문서 생성

### 6. 비동기 지원

**Spring**:
- 기본 MVC는 동기식 (서블릿 기반)
- Spring WebFlux로 리액티브 프로그래밍 지원

**FastAPI**:
- 처음부터 비동기 지원 (`async/await`)
- 이벤트 루프 기반 (성능 이점)
- 동기 코드와 쉽게 혼합 가능

## 🚀 실행 방법

### 1. 환경 설정

```bash
# 가상환경 생성 (선택 사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 개발 모드 실행 (자동 리로드)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 프로덕션 모드 실행

```bash
# 단일 프로세스 (Uvicorn)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 멀티 프로세스 (Gunicorn + UvicornWorker)
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8000
```

### 4. API 문서 접근

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📊 성능 비교 (FastAPI vs Spring Boot)

FastAPI는 비동기 처리와 ASGI 서버 덕분에 I/O 바운드 작업에서 Spring Boot보다 효율적인 리소스 사용을 보입니다:

### 메모리 사용량 (동일 수준의 요청 처리 시)
- **Spring Boot + Tomcat**: ~500-800MB
- **FastAPI + Uvicorn**: ~100-150MB

### 동시성 처리 (1,000 동시 접속 시)
- **Spring Boot**: 스레드 풀 확장 필요 (메모리 증가)
- **FastAPI**: 적은 수의 워커로 효율적 처리 (비동기 이벤트 루프)

### 시작 시간
- **Spring Boot**: 5-30초 (애플리케이션 규모에 따라)
- **FastAPI**: 1-2초 (마이크로서비스에 적합)

## 📚 확장 실험 아이디어

1. **데이터베이스 연동**
   - SQLAlchemy (AsyncSession) + Alembic 마이그레이션
   - Spring의 JPA/Hibernate와 유사한 패턴 구현

2. **인증/인가 시스템**
   - JWT 기반 인증 구현
   - OAuth2 통합
   - 역할 기반 권한 관리

3. **캐싱 계층**
   - Redis 통합 (aioredis)
   - 메모리 캐시 구현
   - Spring의 @Cacheable과 유사한 데코레이터 구현

4. **메시징 & 이벤트**
   - RabbitMQ/Kafka 통합
   - 이벤트 기반 아키텍처 구현
   - 비동기 작업 처리

5. **멀티 테넌시**
   - 테넌트별 요청 분리
   - 테넌트별 데이터 분리
   - Spring의 AbstractRoutingDataSource와 유사 구현

## 🔍 참고 문서

- FastAPI 공식문서: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- ASGI 서버 (Uvicorn): [https://www.uvicorn.org/](https://www.uvicorn.org/)
- Spring MVC 문서: [https://docs.spring.io/spring-framework/reference/web/webmvc.html](https://docs.spring.io/spring-framework/reference/web/webmvc.html)
- Starlette (FastAPI 기반): [https://www.starlette.io/](https://www.starlette.io/)
- Pydantic (타입 검증): [https://docs.pydantic.dev/](https://docs.pydantic.dev/)

## ✍️ 저작 목적

본 프로젝트는 다수의 API 구현이 아니라, **백엔드 프레임워크의 실행 흐름을 체계적으로 학습하기 위한 실험형 구성**을 목표로 설계되었습니다.
