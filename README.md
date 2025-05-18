# FastAPI-Flow

## 📌 프로젝트 개요

**FastAPI-Flow**는 Python 기반의 FastAPI 프레임워크를 활용하여, 실제 FastAPI 내림의 요청 처리 환경과 미들워 동작, 예외 처리, 라우트인구, AOP 유사 기능 등을 **Spring MVC 구조에 대응하는 방식으로 직접 구성하고 실험**하는 학습용 프로젝트입니다.

이 프로젝트는 FastAPI의 자동 동작 이며을 직접 구성함으로써, 프레임워크의 내림 구조를 더 깊이 이해하고 실무에서의 판단력을 높이는 것을 목표로 합니다.

---

## 🌟 학습 목표

- ASGI 기반 요청 처리 환경 구조 파악 (Uvicorn → Middleware → Dependency → Router → Handler)
- Spring MVC의 DispatcherServlet, Filter, Interceptor, Controller 환경과 1:1 맞춤 개념 실습
- FastAPI의 미들워, 의종성 주입(Interceptor 유사), 전역 예외 처리, 데코레이터 기능을 실험
- 모든 환경을 로그와 구조화된 문서로 추적 가능
- RESTful API 응답 처리 + HTML 렌더링(Jinja2) 동생 실험

---

## ⚙️ 기술 스택

- Python 3.11+
- FastAPI 0.110.1
- Uvicorn 0.29.0 (ASGI 서버)
- (선택) Jinja2 템플릿
- (선택) aioredis / SQLAlchemy (특정 시련에서 특정)

---

## 🏠 프로젝트 구조

```
fastapi-flow/
├── app/
│   ├── main.py                      # FastAPI 진입점
│   ├── middleware/                 # Filter 대응
│   │   └── logging.py
│   ├── router/                     # Controller 대응
│   │   └── hello.py
│   ├── service/                    # Service 계층
│   │   └── example_service.py
│   ├── exception/                  # 관리적 예외 핸들러
│   │   └── global_handler.py
│   ├── dependency/                 # Interceptor 대응
│   │   └── auth.py
│   └── docs/                       # 환경 문서화 (SpringFlow의 flow-request.md 대응)
│       └── flow-request.md
├── requirements.txt
└── README.md
```

---

## 🔄 요청 처리 환경

```
클라이언트 요청
   ↓
[Uvicorn (ASGI 서버)]
   ↓
[FastAPI 앱]
   ↓
[Middleware (logging 등)]     ← Spring Filter 대응
   ↓
[Dependency (auth 등)]        ← Spring Interceptor 대응
   ↓
[Router → Handler 호출]       ← Spring Controller 대응
   ↓
[예외 발생 시 Exception Handler] ← Spring @ControllerAdvice 대응
```

---

## 🥺 실험 요소 및 대응 매형

| Spring 구조 요소      | FastAPI 구조 방식                      | 실험 대상 파일                |
| --------------------- | -------------------------------------- | ----------------------------- |
| `DispatcherServlet`   | FastAPI 엔진 (`main.py`)               | `main.py`                     |
| `Filter`              | Middleware (`@app.middleware("http")`) | `middleware/logging.py`       |
| `HandlerInterceptor`  | Dependency Injection (`Depends`)       | `dependency/auth.py`          |
| `@RestController`     | Router + Handler                       | `router/hello.py`             |
| `@ControllerAdvice`   | Global Exception Handler               | `exception/global_handler.py` |
| `@Aspect` / `@Around` | Custom Decorator                       | `log_execution` 등 컨스텀     |
| `@Transactional`      | DB 특정 처리 실험 예정                 | `service/example_service.py`  |

---

## 📚 확장 가능 실험 항목

- Redis 기반 분산 랩 실험 (`redlock-py`, `aioredis`)
- SQLAlchemy + AsyncSession으로 특정 특정 시험
- Jinja2 기반 View 렌더링 → ViewResolver 대응
- Request/Response 컨트롤 개정 (`Response` 클래스 사용)
- Gunicorn + UvicornWorker 조합 테스트 (머티 프로세스)

---

## 🔍 참고 문서

- FastAPI 공식문서: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- ASGI 서버 (Uvicorn): [https://www.uvicorn.org/](https://www.uvicorn.org/)
- Spring DispatcherServlet 환경 공식 문서: [https://docs.spring.io/spring-framework/](https://docs.spring.io/spring-framework/)

---

## ✍️ 저작 목적

본 프로젝트는 다수의 API 구현이 아니라, **백어드 프레임워크의 실행 환경을 체계적으로 학습하기 위한 실험형 구성**을 목표로 설계되어있습니다.
Spring을 사용하는 개발자, 혹은 FastAPI의 내림 구조를 명확히 이해하고 시스템적 획의를 높이고 싶은 모든 백어드 개발자에게 추천됩니다.
