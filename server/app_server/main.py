import asyncio
import json
from contextlib import asynccontextmanager

import app_server.share.global_value as g
import zmq
import zmq.asyncio  # asyncio と統合: PULL の recv を非同期化し、同一イベントループで Lock/Queue と共存
from app_server.config.di import DI
from app_server.config.trading_settings import get_zmq_recv_port, get_zmq_send_port
from app_server.domain.core_logic.base import CoreLogic
from app_server.routers import trading_router
from app_server.share.logger_util import get_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = get_logger()

# ZeroMQ 用（lifespan で初期化）
_zmq_context: zmq.Context | None = None
_zmq_push_socket: zmq.Socket | None = None


async def _zmq_receiver(recv_port: int) -> None:
    """ZeroMQ PULL でティック・注文結果・価格情報・注文情報・ペンディング約定通知を受信し、コアロジックに渡す"""
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
                        if isinstance(data, dict):
                            msg_type = data.get("type")
                            request_id = data.get("request_id")
                            # 応答待ちキューに登録されていればキューへ投入
                            if request_id and g.pending_response_queues:
                                queue = g.pending_response_queues.get(request_id)
                                if queue is not None:
                                    try:
                                        queue.put_nowait(raw)
                                    except Exception:
                                        pass
                            if msg_type == "order_result":
                                core_logic.on_order_result(raw)
                                continue
                            if msg_type == "price_info" or msg_type == "order_info_list":
                                continue
                            if msg_type == "pending_opened":
                                core_logic.on_pending_opened(raw)
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
    """起動時に ZeroMQ を初期化し、受信タスクを開始する"""
    global _zmq_context, _zmq_push_socket, g
    g.pending_response_queues = {}
    g.pending_response_lock = asyncio.Lock()
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
