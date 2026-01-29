"""MT4 実機用命令部（設計書 4.5, サンプル send_to_mql4 をラップ）"""

import json

import zmq
from app_server.model.trading import OrderCommand
from app_server.service.order.base import OrderSender
from app_server.share.logger_util import get_logger

logger = get_logger()


class Mt4OrderSender(OrderSender):
    """PUSH ソケットで JSON を MT4 に送信する実機用命令部"""

    def __init__(self, socket: zmq.Socket) -> None:
        """PUSH ソケットを受け取って初期化する。"""
        self._push_socket = socket

    def send_order(self, order_command: OrderCommand) -> bool:
        payload = order_command.model_dump(mode="json", exclude_none=True)
        # action=ORDER のとき type を文字列で、sl/tp は 0 のとき省略可
        if payload.get("action") == "ORDER" and payload.get("price") == 0:
            payload["price"] = 0  # 成行のため 0 のまま
        cmd_str = json.dumps(payload, ensure_ascii=False)
        try:
            self._push_socket.send_string(cmd_str, zmq.NOBLOCK)
            logger.info("MT4へ送信: %s", cmd_str)
            return True
        except zmq.ZMQError as e:
            logger.error("送信エラー: %s", e)
            return False
