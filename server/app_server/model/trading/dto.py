"""売買用データモデル"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


# ----- 5.1 ティック・価格データ -----
class TickDto(BaseModel):
    """ティックデータ（MT4から受信した1件をパースした形）"""

    symbol: str  # 通貨ペア名（例: "USDJPY"）
    bid: float  # 売値（売り注文の約定価格）
    ask: float  # 買値（買い注文の約定価格）
    spread: int  # スプレッド（ask - bid をポイント単位で表現）
    time: datetime | str  # ティック受信時刻（パース済み or 文字列）


# ----- 5.2 シグナル -----
class Signal(str, Enum):
    """戦略が返すシグナル"""

    BUY = "BUY"  # 買いシグナル
    SELL = "SELL"  # 売りシグナル
    HOLD = "HOLD"  # 様子見（何もしない）


class SignalResult(BaseModel):
    """シグナル＋注文量等（必要に応じて使用）"""

    signal: Signal  # 売買シグナル（BUY/SELL/HOLD）
    lots: float = 0.01  # 注文ロット数（取引量）
    sl: float = 0.0  # ストップロス価格（損切りライン）
    tp: float = 0.0  # テイクプロフィット価格（利確ライン）


# ----- 5.3 注文・約定 -----
class OrderCommand(BaseModel):
    """MT4へ送る注文コマンド（ORDER / CLOSE / PRICE_INFO / ORDER_INFO）"""

    action: Literal["ORDER", "CLOSE", "PRICE_INFO", "ORDER_INFO"]
    request_id: str | None = None  # 応答検証用（ORDER/CLOSE/PRICE_INFO/ORDER_INFO で必須）
    symbol: str = ""  # 通貨ペア名
    type: Literal["BUY", "SELL"] | None = None  # 売買方向（action=ORDER の場合に使用）
    lots: float = 0.01  # 注文ロット数
    price: float = 0.0  # 指定価格（成行の場合は0）
    sl: float = 0.0  # ストップロス価格
    tp: float = 0.0  # テイクプロフィット価格
    ticket: int | None = None  # チケット番号（action=CLOSE/ORDER_INFO で使用）


class OrderResult(BaseModel):
    """MT4から返ってくる注文結果"""

    type: Literal["order_result"] = "order_result"  # メッセージ種別（固定値）
    request_id: str  # 対応するリクエストの request_id
    ticket: int  # MT4が発行したチケット番号
    status: str  # 注文結果ステータス（SUCCESS, FAILED, CLOSED 等）


class PriceInfo(BaseModel):
    """MT4からの価格情報応答（action=PRICE_INFO の応答）"""

    type: Literal["price_info"] = "price_info"
    request_id: str
    symbol: str
    point: float
    digits: int
    pips: float


class OrderInfo(BaseModel):
    """注文1件の情報（order_info_list の orders 要素）"""

    ticket: int
    status: str  # "OK" = 取得成功
    symbol: str
    order_type: str  # BUY / SELL / BUY_LIMIT / SELL_LIMIT / BUY_STOP / SELL_STOP
    lots: float
    open_price: float
    sl: float = 0.0
    tp: float = 0.0
    open_time: str = ""
    close_time: str = ""
    profit: float = 0.0


class OrderInfoList(BaseModel):
    """MT4からの注文情報応答（action=ORDER_INFO の応答）"""

    type: Literal["order_info_list"] = "order_info_list"
    request_id: str
    count: int
    orders: list[OrderInfo]


class PendingOpened(BaseModel):
    """ペンディング約定通知（指値・逆指値が約定してポジションオープンした際の通知）"""

    type: Literal["pending_opened"] = "pending_opened"
    ticket: int
    symbol: str
    order_type: str  # BUY_LIMIT / SELL_LIMIT / BUY_STOP / SELL_STOP
    lots: float
    open_price: float
    open_time: str


# ----- 売買結果CSV・損益集計CSV 用 -----
class TradeResultRow(BaseModel):
    """売買結果CSVの1行（都度記録用）"""

    executed_at: str = ""  # 約定日時（ISO形式文字列）
    symbol: str = ""  # 通貨ペア名
    side: Literal["BUY", "SELL"] = "BUY"  # 売買方向
    lots: float = 0.0  # 約定ロット数
    price: float = 0.0  # 約定価格
    ticket: int = 0  # チケット番号
    status: str = ""  # 約定ステータス
    pnl: float = 0.0  # 損益（決済時に確定）
    memo: str = ""  # 備考・メモ


class PnlSummaryRow(BaseModel):
    """損益集計CSVの1行"""

    period_type: str = ""  # 集計期間種別（daily / weekly / monthly）
    period_start: str = ""  # 集計期間の開始日
    period_end: str = ""  # 集計期間の終了日
    trade_count: int = 0  # 取引回数
    total_pnl: float = 0.0  # 合計損益
    win_count: int = 0  # 勝ちトレード数
    loss_count: int = 0  # 負けトレード数
