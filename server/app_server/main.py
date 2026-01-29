import asyncio
import json
from contextlib import asynccontextmanager

import zmq
import zmq.asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app_server.share.global_value as g
from app_server.config.di import DI
from app_server.config.trading_settings import get_zmq_recv_port, get_zmq_send_port
from app_server.routers import trading_router
from app_server.service.core_logic.base import CoreLogic
from app_server.share.logger_util import get_logger

logger = get_logger()

# ZeroMQ 用（lifespan で初期化）
_zmq_context: zmq.Context | None = None
_zmq_push_socket: zmq.Socket | None = None


async def _zmq_receiver(recv_port: int) -> None:
    """ZeroMQ PULL でティック・注文結果を受信し、コアロジックに渡す（設計書 3.3）"""
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.PULL)
    socket.bind(f"tcp://*:{recv_port}")
    logger.info("ZeroMQ PULL ソケット起動: ポート %s", recv_port)
    core_logic = g.injector.resolve(CoreLogic)
    try:
        while True:
            try:
                message = await socket.recv_string()
                raw = (message or "").strip()
                logger.info("ZeroMQ 受信メッセージ: %s", raw)
                if raw.startswith("{"):
                    try:
                        data = json.loads(raw)
                        if (
                            isinstance(data, dict)
                            and data.get("type") == "order_result"
                        ):
                            core_logic.on_order_result(raw)
                            continue
                    except json.JSONDecodeError:
                        pass
                core_logic.on_tick(raw)
            except zmq.ZMQError as e:
                logger.error("ZeroMQエラー: %s", e)
                await asyncio.sleep(1)
    finally:
        socket.close()
        ctx.term()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """起動時に ZeroMQ を初期化し、受信タスクを開始する（設計書 2.2, 11.1）"""
    global _zmq_context, _zmq_push_socket, g
    recv_port = get_zmq_recv_port()
    send_port = get_zmq_send_port()
    _zmq_context = zmq.Context()
    _zmq_push_socket = _zmq_context.socket(zmq.PUSH)
    _zmq_push_socket.bind(f"tcp://*:{send_port}")
    logger.info("ZeroMQ PUSH ソケット起動: ポート %s", send_port)
    # DI を PUSH ソケット付きで再初期化（OrderSender が socket を必要とするため）
    g.injector = DI(zmq_push_socket=_zmq_push_socket)
    task = asyncio.create_task(_zmq_receiver(recv_port))
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
from app_server.exception.exception_handler import (  # noqa: E402, F401
    http_exception_handler,
    validation_exception_handler,
)

app.include_router(trading_router.router)
