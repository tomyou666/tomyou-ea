"""命令部の抽象基底クラス（設計書 4.5）"""

from abc import ABCMeta, abstractmethod

from app_server.model.trading import OrderCommand, Signal, SignalResult


class OrderSender(metaclass=ABCMeta):
    """シグナルを MT4 が理解する注文コマンドに変換し送信する命令部の基底クラス"""

    @abstractmethod
    def send_order(self, order_command: OrderCommand) -> bool:
        """注文コマンドを MT4 に送信する。

        Args:
            order_command: 送信する注文コマンド

        Returns:
            送信成功なら True、失敗なら False
        """
        raise NotImplementedError

    def build_order_command(
        self,
        signal: Signal | SignalResult,
        symbol: str,
        lots: float = 0.01,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
    ) -> OrderCommand:
        """シグナルから OrderCommand を組み立てる（共通ヘルパー）。"""
        if isinstance(signal, SignalResult):
            s = signal.signal
            lots = signal.lots
            sl = signal.sl
            tp = signal.tp
        else:
            s = signal
        if s == Signal.HOLD:
            raise ValueError("HOLD では注文コマンドを組み立てません")
        return OrderCommand(
            action="ORDER",
            symbol=symbol,
            type="BUY" if s == Signal.BUY else "SELL",
            lots=lots,
            price=price,
            sl=sl,
            tp=tp,
        )
