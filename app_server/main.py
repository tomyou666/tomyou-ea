from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app_server.share.global_value as g
from app_server.config.di import DI
from app_server.routers import task_router

app = FastAPI(
    title="FastAPI server",
    # lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# DIの初期化
g.injector = DI()

# CORSを回避するために追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 例外ハンドラの読み込み
from app_server.app.exception_handler import http_exception_handler, validation_exception_handler  # noqa: F401

# ミドルウェアの読み込み
from app_server.app.middleware import add_process_time_header  # noqa: F401

app.include_router(task_router.router)
