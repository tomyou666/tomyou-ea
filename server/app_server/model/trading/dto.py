"""売買用データモデル（設計書 第5章）"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


# ----- 5.1 ティック・価格データ -----
class TickDto(BaseModel):
    """ティックデータ（MT4から受信した1件をパースした形）"""

    symbol: str
    bid: float
    ask: float
    spread: int
    time: datetime | str  # パース済み


# ----- 5.2 シグナル -----
class Signal(str, Enum):
    """戦略が返すシグナル"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalResult(BaseModel):
    """シグナル＋注文量等（必要に応じて使用）"""

    signal: Signal
    lots: float = 0.01
    sl: float = 0.0
    tp: float = 0.0


# ----- 5.3 注文・約定 -----
class OrderCommand(BaseModel):
    """MT4へ送る注文コマンド（設計書 3.2.2, 3.2.3）"""

    action: Literal["ORDER", "CLOSE"]
    symbol: str = ""
    type: Literal["BUY", "SELL"] | None = None  # action=ORDER の場合
    lots: float = 0.01
    price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    ticket: int | None = None  # action=CLOSE の場合


class OrderResult(BaseModel):
    """MT4から返ってくる注文結果（設計書 3.2.4）"""

    type: Literal["order_result"] = "order_result"
    ticket: int
    status: str  # SUCCESS, FAILED, CLOSED 等


# ----- 8章 売買結果CSV・損益集計CSV 用 -----
class TradeResultRow(BaseModel):
    """売買結果CSVの1行（都度記録用）"""

    executed_at: str = ""  # 約定日時
    symbol: str = ""
    side: Literal["BUY", "SELL"] = "BUY"
    lots: float = 0.0
    price: float = 0.0
    ticket: int = 0
    status: str = ""
    pnl: float = 0.0
    memo: str = ""


class PnlSummaryRow(BaseModel):
    """損益集計CSVの1行"""

    period_type: str = ""  # daily / weekly / monthly
    period_start: str = ""
    period_end: str = ""
    trade_count: int = 0
    total_pnl: float = 0.0
    win_count: int = 0
    loss_count: int = 0
