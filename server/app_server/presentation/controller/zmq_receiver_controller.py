"""ZeroMQ PULL でティック・注文結果等を受信し、application 層に渡す"""

import asyncio
import json

import app_server.share.global_value as g
import zmq
import zmq.asyncio
from app_server.application.trading_service.base import TradingServiceBase
from app_server.share.logger_util import get_logger

logger = get_logger()


async def run_zmq_receiver(recv_port: int) -> None:
    """ZeroMQ PULL でティック・注文結果・価格情報・注文情報・ペンディング約定通知を受信し、TradingService に渡す。"""
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.PULL)
    socket.bind(f"tcp://*:{recv_port}")
    logger.info("ZeroMQ PULL ソケット起動: ポート %s", recv_port)
    trading_service: TradingServiceBase = g.injector.resolve(TradingServiceBase)
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
                            if request_id and g.pending_response_queues:
                                queue = g.pending_response_queues.get(request_id)
                                if queue is not None:
                                    try:
                                        queue.put_nowait(raw)
                                    except Exception:
                                        pass
                            if msg_type == "order_result":
                                trading_service.on_order_result(raw)
                                continue
                            if data.get("status") == "FAILED" and isinstance(
                                data.get("request_id"), str
                            ):
                                trading_service.on_order_result(raw)
                                continue
                            if msg_type in {"price_info", "order_info_list"}:
                                continue
                            if msg_type == "pending_opened":
                                trading_service.on_pending_opened(raw)
                                continue
                    except json.JSONDecodeError:
                        pass
                trading_service.on_tick(raw)
            except zmq.ZMQError as e:
                logger.error("ZeroMQエラー: %s", e)
                await asyncio.sleep(1)
    finally:
        socket.close()
        ctx.term()
