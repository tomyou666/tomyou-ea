"""MT4 実機用命令部（ORDER / CLOSE / PRICE_INFO / ORDER_INFO）"""

import asyncio
import json
import uuid

import zmq

import app_server.share.global_value as g
from app_server.config.trading_settings import get_retry_count, get_response_timeout_sec
from app_server.model.trading import (
    OrderCommand,
    OrderInfo,
    OrderInfoList,
    PriceInfo,
)
from app_server.service.order.base import Mt4RequestTimeoutError, OrderSender
from app_server.share.logger_util import get_logger

logger = get_logger()


async def _wait_response(request_id: str) -> str | None:
    """pending_response_queues に登録された request_id の応答をタイムアウト付きで待つ。"""
    if g.pending_response_queues is None:
        return None
    timeout = get_response_timeout_sec()
    queue = g.pending_response_queues.get(request_id)
    if queue is None:
        return None
    try:
        return await asyncio.wait_for(queue.get(), timeout=timeout)
    except TimeoutError:
        return None


async def _register_request(request_id: str) -> asyncio.Queue:
    """request_id 用のキューを登録する。"""
    if g.pending_response_queues is None:
        g.pending_response_queues = {}
    q: asyncio.Queue = asyncio.Queue()
    if g.pending_response_lock is not None:
        async with g.pending_response_lock:
            g.pending_response_queues[request_id] = q
    else:
        g.pending_response_queues[request_id] = q
    return q


async def _unregister_request(request_id: str) -> None:
    """request_id のキューを削除する。"""
    if g.pending_response_queues is None:
        return
    if g.pending_response_lock is not None:
        async with g.pending_response_lock:
            g.pending_response_queues.pop(request_id, None)
    else:
        g.pending_response_queues.pop(request_id, None)


class Mt4OrderSender(OrderSender):
    """PUSH ソケットで JSON を MT4 に送信する実機用命令部"""

    def __init__(self, socket: zmq.Socket) -> None:
        """PUSH ソケットを受け取って初期化する。"""
        self._push_socket = socket

    def _send_payload(self, payload: dict) -> bool:
        """JSON ペイロードを MT4 に送信する（order 層内部専用）。"""
        cmd_str = json.dumps(payload, ensure_ascii=False)
        try:
            self._push_socket.send_string(cmd_str, zmq.NOBLOCK)
            logger.info("MT4へ送信: %s", cmd_str)
            return True
        except zmq.ZMQError as e:
            logger.error("送信エラー: %s", e)
            return False

    def send_order(self, order_command: OrderCommand) -> bool:
        payload = order_command.model_dump(mode="json", exclude_none=True)
        if payload.get("action") in ("ORDER", "CLOSE") and not payload.get("request_id"):
            payload["request_id"] = f"req-{uuid.uuid4().hex[:12]}"
        if payload.get("action") == "ORDER" and payload.get("price") == 0:
            payload["price"] = 0
        return self._send_payload(payload)

    async def get_price_info(self, symbol: str) -> PriceInfo:
        """PRICE_INFO を送信し、request_id で応答を検証して PriceInfo を返す。"""
        retry_count = get_retry_count()
        last_error: Exception | None = None

        for attempt in range(retry_count):
            request_id = f"price-{uuid.uuid4().hex[:12]}"
            await _register_request(request_id)
            try:
                payload = {
                    "action": "PRICE_INFO",
                    "request_id": request_id,
                    "symbol": symbol,
                }
                if not self._send_payload(payload):
                    last_error = RuntimeError("PRICE_INFO 送信失敗")
                    await _unregister_request(request_id)
                    continue
                raw = await _wait_response(request_id)
                await _unregister_request(request_id)
                if raw is None:
                    last_error = Mt4RequestTimeoutError(
                        f"PRICE_INFO 応答タイムアウト (request_id={request_id})"
                    )
                    logger.warning("PRICE_INFO タイムアウト attempt=%s", attempt + 1)
                    continue
                data = json.loads(raw)
                if not isinstance(data, dict) or data.get("type") != "price_info":
                    last_error = ValueError("応答が price_info ではありません")
                    continue
                if data.get("request_id") != request_id:
                    last_error = ValueError(
                        f"request_id 不一致: 期待 {request_id}, 受信 {data.get('request_id')}"
                    )
                    logger.warning("PRICE_INFO request_id 不一致 attempt=%s", attempt + 1)
                    continue
                return PriceInfo(
                    type="price_info",
                    request_id=data["request_id"],
                    symbol=data["symbol"],
                    point=float(data["point"]),
                    digits=int(data["digits"]),
                    pips=float(data["pips"]),
                )
            except Exception as e:
                last_error = e
                await _unregister_request(request_id)

        raise last_error or Mt4RequestTimeoutError("PRICE_INFO がリトライ上限に達しました")

    async def get_order_info(self, ticket: int | None = None) -> OrderInfoList:
        """ORDER_INFO を送信し、request_id で応答を検証して OrderInfoList を返す。"""
        retry_count = get_retry_count()
        last_error: Exception | None = None

        for attempt in range(retry_count):
            request_id = f"order-{uuid.uuid4().hex[:12]}"
            await _register_request(request_id)
            try:
                payload: dict = {
                    "action": "ORDER_INFO",
                    "request_id": request_id,
                }
                if ticket is not None:
                    payload["ticket"] = ticket
                if not self._send_payload(payload):
                    last_error = RuntimeError("ORDER_INFO 送信失敗")
                    await _unregister_request(request_id)
                    continue
                raw = await _wait_response(request_id)
                await _unregister_request(request_id)
                if raw is None:
                    last_error = Mt4RequestTimeoutError(
                        f"ORDER_INFO 応答タイムアウト (request_id={request_id})"
                    )
                    logger.warning("ORDER_INFO タイムアウト attempt=%s", attempt + 1)
                    continue
                data = json.loads(raw)
                if not isinstance(data, dict) or data.get("type") != "order_info_list":
                    last_error = ValueError("応答が order_info_list ではありません")
                    continue
                if data.get("request_id") != request_id:
                    last_error = ValueError(
                        f"request_id 不一致: 期待 {request_id}, 受信 {data.get('request_id')}"
                    )
                    logger.warning("ORDER_INFO request_id 不一致 attempt=%s", attempt + 1)
                    continue
                orders_raw = data.get("orders", [])
                orders = [
                    OrderInfo(
                        ticket=o.get("ticket", 0),
                        status=o.get("status", ""),
                        symbol=o.get("symbol", ""),
                        order_type=o.get("order_type", ""),
                        lots=float(o.get("lots", 0)),
                        open_price=float(o.get("open_price", 0)),
                        sl=float(o.get("sl", 0)),
                        tp=float(o.get("tp", 0)),
                        open_time=o.get("open_time", ""),
                        close_time=o.get("close_time", ""),
                        profit=float(o.get("profit", 0)),
                    )
                    for o in orders_raw
                ]
                return OrderInfoList(
                    type="order_info_list",
                    request_id=data["request_id"],
                    count=int(data.get("count", 0)),
                    orders=orders,
                )
            except Exception as e:
                last_error = e
                await _unregister_request(request_id)

        raise last_error or Mt4RequestTimeoutError("ORDER_INFO がリトライ上限に達しました")
