"""infrastructure 層: JSON ペイロードを ZMQ で MT4 に送信するのみ（send_payload）"""

import json

import zmq
from app_server.infrastructure.sender.base import PayloadSenderBase
from app_server.share.logger_util import get_logger

logger = get_logger()


class Mt4PayloadSender(PayloadSenderBase):
    """JSON ペイロードを MT4 に ZMQ で送信する。役割は send_payload のみ。"""

    def __init__(self, socket: zmq.Socket) -> None:
        self._push_socket = socket

    def send_payload(self, payload: dict) -> bool:
        """ペイロードを JSON 化して ZMQ で送信する。"""
        cmd_str = json.dumps(payload, ensure_ascii=False)
        try:
            self._push_socket.send_string(cmd_str, zmq.NOBLOCK)
            logger.info("MT4へ送信: %s", cmd_str)
            return True
        except zmq.ZMQError as e:
            logger.error("送信エラー: %s", e)
            return False
