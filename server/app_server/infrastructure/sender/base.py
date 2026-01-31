"""JSON ペイロードを外部に送信するインターフェース"""

from abc import ABCMeta, abstractmethod


class PayloadSenderBase(metaclass=ABCMeta):
    """JSON ペイロードを外部に送信するインターフェース"""

    @abstractmethod
    def send_payload(self, payload: dict) -> bool:
        """ペイロードを送信する。成功なら True"""
        raise NotImplementedError
