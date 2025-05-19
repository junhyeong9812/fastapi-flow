# FastAPI-Flow 보안 확장 가이드

## 📌 보안 확장 개요

FastAPI-Flow 프로젝트에 Spring Security와 유사한 보안 기능을 확장 모듈로 추가했습니다. 이 문서는 추가된 보안 기능과 사용 방법에 대해 설명합니다.

> **중요**: 기존 코드는 모두 그대로 유지됩니다. 보안 기능은 완전히 별도의 모듈로 구현되어 기존 코드에 영향을 주지 않습니다.

주요 보안 기능:
- JWT 기반 인증
- 역할 기반 접근 제어 (RBAC)
- 권한 기반 접근 제어 (PBAC)
- 리소스 소유자 검증
- Redis를 활용한 토큰 관리
- 보안 미들웨어 (헤더, XSS 보호 등)
- 속도 제한 기능

## 🏛️ 아키텍처 및 흐름

### 보안 처리 흐름

```
클라이언트 요청
   ↓
[Uvicorn ASGI 서버]
   ↓
[FastAPI 애플리케이션]
   ↓
[Security Middleware] - 보안 헤더 설정, XSS 보호 등
   ↓
[Rate Limit Middleware] - 요청 속도 제한
   ↓
[Logging Middleware] - 요청 로깅
   ↓
[라우터 핸들러]
   ↓
[Auth Dependencies] - 토큰 검증, 권한 확인 등
   ↓
[컨트롤러 로직 실행]
   ↓
[응답 생성 및 반환]
```

### Spring Security와의 비교

| Spring Security 컴포넌트        | FastAPI-Flow 구현                    | 설명                               |
|-----------------------------|----------------------------------|----------------------------------|
| SecurityConfig              | app/config/settings.py          | 보안 설정 관리                        |
| JwtTokenProvider            | app/security/jwt.py             | JWT 토큰 생성 및 검증                  |
| UserDetailsService          | AuthDependency.get_current_user | 현재 사용자 정보 로드                    |
| Authentication              | TokenPayload                    | 인증 정보 모델                        |
| AuthenticationManager       | authenticate_user               | 사용자 인증 로직                       |
| Filter                      | Middleware                      | 요청 전/후 처리                       |
| @PreAuthorize("hasRole()") | AuthDependency.has_role         | 역할 기반 권한 검사                     |
| @Secured                    | 라우터 레벨 dependencies            | API 보호                           |
| AccessDeniedHandler         | AppException 핸들러               | 접근 거부 처리                        |
| AuthenticationEntryPoint    | AppException 핸들러               | 인증 실패 처리                        |
| RefreshTokenRepository      | RedisClient                    | 토큰 저장소                          |

## 📁 프로젝트 구조

보안 확장을 위해 추가된 파일들:

```
app/
├── config/                        # 설정 관련
│   ├── redis.py                   # Redis 클라이언트 설정
│   └── settings.py                # 애플리케이션 설정
├── middleware/                    
│   └── security.py                # 보안 미들웨어 (헤더, XSS 보호 등)
├── models/                        
│   └── user.py                    # 사용자 관련 모델
├── router/                        
│   ├── auth.py                    # 인증 관련 API 엔드포인트
│   ├── protected.py               # 보호된 API 엔드포인트
│   └── security_test.py           # 보안 테스트 API 엔드포인트
├── security/                      # 보안 관련 핵심 모듈
│   ├── auth.py                    # 인증/인가 의존성 (Dependency)
│   └── jwt.py                     # JWT 토큰 서비스
```

## 🧩 주요 컴포넌트

### 1. JWT 토큰 서비스 (`app/security/jwt.py`)

Spring Security의 JwtTokenProvider와 유사한 역할을 하는 클래스입니다.

```python
# JWT 토큰 생성
access_token = JWTTokenService.create_access_token(
    subject=user_id,
    role="ADMIN"
)

# 토큰 검증
token_payload = JWTTokenService.verify_token(token)

# 비밀번호 해싱 및 검증
hashed_password = JWTTokenService.get_password_hash(password)
is_valid = JWTTokenService.verify_password(password, hashed_password)
```

### 2. 인증 의존성 (`app/security/auth.py`)

Spring Security의 인증 및 인가 필터와 유사한 역할을 하는 의존성 주입 클래스입니다.

```python
# 라우터에 인증 적용
@router.get("/protected", dependencies=[Depends(AuthDependency.get_token_payload)])
async def protected_route():
    return {"message": "인증된 사용자만 접근 가능"}

# 현재 사용자 정보 사용
@router.get("/me")
async def get_me(current_user: dict = Depends(AuthDependency.get_current_user)):
    return {"user": current_user}

# 역할 기반 접근 제어
@router.get("/admin", dependencies=[Depends(AuthDependency.has_role("ADMIN"))])
async def admin_only():
    return {"message": "관리자 전용 API"}
```

### 3. 보안 미들웨어 (`app/middleware/security.py`)

Spring Security의 필터와 유사한 역할을 하는 미들웨어입니다.

```python
# 보안 헤더 미들웨어
app.middleware("http")(security_middleware)

# XSS 보호 미들웨어
app.middleware("http")(xss_protection_middleware)

# 속도 제한 미들웨어
app.middleware("http")(rate_limit_middleware)
```

### 4. 인증 라우터 (`app/router/auth.py`)

사용자 인증 및 등록 API를 제공합니다.

```python
# 로그인 API
@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # 사용자 인증 및 토큰 발급
    ...

# 회원가입 API
@router.post("/register", response_model=UserResponse)
async def register(user_create: UserCreate):
    # 새 사용자 등록
    ...

# 토큰 갱신 API
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    # 리프레시 토큰으로 새 액세스 토큰 발급
    ...
```

## 📋 사용 방법

### 1. Docker Compose로 Redis 시작

```bash
# docker-compose.yml 파일이 있는 디렉토리에서
docker-compose up -d
```

### 2. 애플리케이션 실행

```bash
# 개발 모드
uvicorn app.main:app --reload

# 또는 Python 모듈로 실행
python -m app.main
```

### 3. 인증 및 API 사용 예시

#### 회원가입

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","password":"Password123!","email":"new@example.com","full_name":"New User","role":"USER"}'
```

#### 로그인 및 토큰 획득

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

#### 보호된 API 호출

```bash
curl -X GET http://localhost:8000/api/protected/me \
  -H "Authorization: Bearer 여기에_받은_토큰_입력"
```

#### 관리자 전용 API 호출

```bash
curl -X GET http://localhost:8000/api/protected/admin \
  -H "Authorization: Bearer 관리자_토큰_입력"
```

## 🧪 테스트 엔드포인트

`/api/security-test/` 경로 아래에 다양한 보안 기능 테스트를 위한 엔드포인트가 있습니다:

- **공개 엔드포인트**: `/api/security-test/public`
- **JWT 인증 테스트**: `/api/security-test/jwt-auth`
- **사용자 정보 테스트**: `/api/security-test/user-info`
- **관리자 권한 테스트**: `/api/security-test/admin-only`
- **권한 테스트**: `/api/security-test/permission-test`
- **리소스 소유자 테스트**: `/api/security-test/resource/{resource_id}`
- **보안 헤더 테스트**: `/api/security-test/security-headers-test`
- **토큰 정보 테스트**: `/api/security-test/token-info`

## 🔧 주요 설정 파일

### 애플리케이션 설정 (`app/config/settings.py`)

```python
class SecuritySettings(BaseSettings):
    # JWT 설정
    SECRET_KEY: str = "..."
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS 설정
    CORS_ORIGINS: List[str] = ["*"]
    # ... 기타 설정
```

### Redis 설정 (`app/config/redis.py`)

```python
class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = "redispassword"
    db: int = 0
    # ... 기타 설정
```

## 📄 참고

* 기존 `dependency/auth.py` 파일은 변경되지 않았습니다.
* 이 확장 모듈은 기존 코드와 완전히 독립적으로 작동합니다.
* 실제 프로덕션 환경에서는 보안 키, 비밀번호 등을 환경 변수로 설정해야 합니다.