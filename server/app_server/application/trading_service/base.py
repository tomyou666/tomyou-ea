"""トレード処理の制御（application 層）の抽象基底クラス"""

from abc import ABCMeta, abstractmethod

from app_server.models.trading import Signal, SignalResult, TradeResultRow


class TradingServiceBase(metaclass=ABCMeta):
    """受信→加工→戦略→命令のフローと、CSV記録・集計のインターフェースを定義する基底クラス"""

    @abstractmethod
    def on_tick(self, raw: str) -> Signal | SignalResult | None:
        """生ティック（CSV文字列）を受け、加工→戦略→命令まで処理する。
        シグナルが BUY/SELL の場合はその Signal または SignalResult を返す。HOLD または処理しない場合は None。"""
        raise NotImplementedError

    @abstractmethod
    def on_order_result(self, raw: str) -> None:
        """MT4 から返ってきた注文結果（JSON文字列）を受け、request_id を検証し売買結果CSVに記録する。"""
        raise NotImplementedError

    @abstractmethod
    def on_pending_opened(self, raw: str) -> None:
        """ペンディング約定通知（指値・逆指値が約定してポジションオープンした際の JSON）を受け、ポジション管理・状態更新に利用する。"""
        raise NotImplementedError

    @abstractmethod
    def append_trade_result(self, row: TradeResultRow) -> None:
        """売買結果を1行追記する。"""
        raise NotImplementedError

    @abstractmethod
    def output_pnl_summary(self, period_type: str = "daily") -> None:
        """損益集計を行い、集計結果CSVを出力する。period_type: daily / weekly / monthly"""
        raise NotImplementedError
