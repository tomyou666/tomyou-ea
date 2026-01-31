import asyncio
from contextlib import asynccontextmanager

import app_server.share.global_value as g
import zmq
from app_server.config.di import DI
from app_server.config.trading_settings import get_zmq_recv_port, get_zmq_send_port
from app_server.presentation.controller.zmq_receiver_controller import run_zmq_receiver
from app_server.presentation.routers import trading_router
from app_server.share.logger_util import get_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = get_logger()

# ZeroMQ 用（lifespan で初期化）
_zmq_context: zmq.Context | None = None
_zmq_push_socket: zmq.Socket | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """起動時に ZeroMQ を初期化し、受信タスクを開始する（presentation 層の controller 経由）。"""
    global _zmq_context, _zmq_push_socket
    g.pending_response_queues = {}
    g.pending_response_lock = asyncio.Lock()
    recv_port = get_zmq_recv_port()
    send_port = get_zmq_send_port()
    _zmq_context = zmq.Context()
    _zmq_push_socket = _zmq_context.socket(zmq.PUSH)
    _zmq_push_socket.bind(f"tcp://*:{send_port}")
    logger.info("ZeroMQ PUSH ソケット起動: ポート %s", send_port)
    g.injector = DI(zmq_push_socket=_zmq_push_socket)
    task = asyncio.create_task(run_zmq_receiver(recv_port))
    logger.info("ZeroMQ 受信タスク開始")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    if _zmq_push_socket:
        _zmq_push_socket.close()
        _zmq_push_socket = None
    if _zmq_context:
        _zmq_context.term()
        _zmq_context = None
    logger.info("ZeroMQ リソース解放完了")


app = FastAPI(
    title="FastAPI server",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# DIの初期化（起動時は socket なし。lifespan で再初期化される）
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
from app_server.handler.exception_handler import (  # noqa: E402, F401
    http_exception_handler,
    validation_exception_handler,
)

app.include_router(trading_router.router)
