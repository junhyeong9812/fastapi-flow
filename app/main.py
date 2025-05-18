# app/main.py
from fastapi import FastAPI
from app.middleware.logging import logging_middleware
from app.router.hello import router as hello_router
from app.exception.global_handler import register_exception_handlers

app = FastAPI()

# 미들웨어 등록
app.middleware("http")(logging_middleware)

# 라우터 등록
app.include_router(hello_router)

# 예외 핸들러 등록
register_exception_handlers(app)
