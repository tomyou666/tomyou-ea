"""命令部の抽象基底クラス"""

from abc import ABCMeta, abstractmethod

from app_server.models.trading import OrderCommand, OrderInfoList, PriceInfo, Signal, SignalResult


class OrderSender(metaclass=ABCMeta):
    """MT4 への各種命令（ORDER / CLOSE / PRICE_INFO / ORDER_INFO）を送信する命令部の基底クラス"""

    @abstractmethod
    def send_order(self, order_command: OrderCommand) -> bool:
        """注文コマンド（ORDER / CLOSE）を MT4 に送信する。

        Args:
            order_command: 送信する注文コマンド

        Returns:
            送信成功なら True、失敗なら False

        """
        raise NotImplementedError

    @abstractmethod
    async def get_price_info(self, symbol: str) -> PriceInfo:
        """PRICE_INFO を送信し、request_id で応答を検証して PriceInfo を返す。"""
        raise NotImplementedError

    @abstractmethod
    async def get_order_info(self, ticket: int | None = None) -> OrderInfoList:
        """ORDER_INFO を送信し、request_id で応答を検証して OrderInfoList を返す。ticket 省略時は全注文。"""
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
