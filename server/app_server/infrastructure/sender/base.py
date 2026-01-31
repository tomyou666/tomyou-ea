"""infrastructure 層: JSON ペイロードを外部に送信するインターフェース"""

from abc import ABCMeta, abstractmethod


class PayloadSenderBase(metaclass=ABCMeta):
    """JSON ペイロードを外部に送信するインターフェース。実装は infrastructure 層に配置。"""

    @abstractmethod
    def send_payload(self, payload: dict) -> bool:
        """ペイロードを送信する。成功なら True。"""
        raise NotImplementedError
