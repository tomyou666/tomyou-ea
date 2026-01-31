"""本番用コアロジック：ZeroMQ 受信と連携、売買結果CSV・損益集計CSV"""

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app_server.config.trading_settings import (
    get_pnl_summary_dir,
    get_trade_result_dir,
    get_trade_result_file_per_day,
)
from app_server.model.trading import (
    OrderResult,
    PnlSummaryRow,
    Signal,
    SignalResult,
    TickDto,
    TradeResultRow,
)
from app_server.service.core_logic.base import CoreLogic
from app_server.service.order.base import OrderSender
from app_server.service.processor.base import Processor
from app_server.service.strategy.base import Strategy
from app_server.share.logger_util import get_logger
from injector import inject

logger = get_logger()

TRADE_RESULT_HEADER = [
    "executed_at",
    "symbol",
    "side",
    "lots",
    "price",
    "ticket",
    "status",
    "pnl",
    "memo",
]
PNL_SUMMARY_HEADER = [
    "period_type",
    "period_start",
    "period_end",
    "trade_count",
    "total_pnl",
    "win_count",
    "loss_count",
]


@inject
@dataclass
class TradingCore(CoreLogic):
    """加工部・戦略部・命令部を組み合わせ、受信→加工→戦略→命令とCSV記録・集計を行う。

    @inject により Processor, Strategy, OrderSender が DI によって自動的に注入される。
    """

    processor: Processor
    strategy: Strategy
    order_sender: OrderSender

    def __post_init__(self) -> None:
        self._result_dir = Path(get_trade_result_dir())
        self._pnl_dir = Path(get_pnl_summary_dir())
        self._file_per_day = get_trade_result_file_per_day()
        self._result_dir.mkdir(parents=True, exist_ok=True)
        self._pnl_dir.mkdir(parents=True, exist_ok=True)

    def _trade_result_path(self) -> Path:
        if self._file_per_day:
            return (
                self._result_dir
                / f"trade_results_{datetime.now().strftime('%Y%m%d')}.csv"
            )
        return self._result_dir / "trade_results.csv"

    def get_trade_result_path(self) -> Path:
        """売買結果CSVの出力パスを返す（テスト・呼び出し元用）。"""
        return self._trade_result_path()

    def get_result_dir(self) -> Path:
        """売買結果CSVの出力ディレクトリを返す（テスト・呼び出し元用）。"""
        return self._result_dir

    def get_pnl_dir(self) -> Path:
        """損益集計CSVの出力ディレクトリを返す（テスト・呼び出し元用）。"""
        return self._pnl_dir

    def on_tick(self, raw: str) -> Optional[Signal | SignalResult]:
        parsed = self.processor.parse(raw)
        if parsed is None:
            return None
        tick = parsed if isinstance(parsed, TickDto) else None
        if tick is None:
            return None
        try:
            out = self.strategy.next(tick, context=None)
            signal = out.signal if isinstance(out, SignalResult) else out
            if signal == Signal.HOLD:
                return None
            symbol = tick.symbol
            lots = out.lots if isinstance(out, SignalResult) else 0.01
            sl = out.sl if isinstance(out, SignalResult) else 0.0
            tp = out.tp if isinstance(out, SignalResult) else 0.0
            price = 0.0  # 成行
            cmd = self.order_sender.build_order_command(
                out, symbol, lots=lots, price=price, sl=sl, tp=tp
            )
            if self.order_sender.send_order(cmd):
                logger.info("シグナルに基づき注文送信: %s %s", signal, symbol)
            # 売買結果の記録は MT4 から order_result 受信時（on_order_result）で行う
            return out
        except Exception as e:
            logger.warning("戦略処理中の例外（ティックスキップ）: %s", e)
            return None

    def on_order_result(self, raw: str) -> None:
        try:
            data = json.loads(raw)
            if data.get("type") != "order_result":
                return
            request_id = data.get("request_id", "")
            res = OrderResult(
                type="order_result",
                request_id=request_id,
                ticket=data.get("ticket", 0),
                status=data.get("status", ""),
            )
            row = TradeResultRow(
                executed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                symbol="",
                side="BUY",
                lots=0.0,
                price=0.0,
                ticket=res.ticket,
                status=res.status,
                pnl=0.0,
                memo="order_result",
            )
            self.append_trade_result(row)
            logger.info(
                "注文結果受信: request_id=%s ticket=%s status=%s",
                res.request_id,
                res.ticket,
                res.status,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("注文結果パースエラー: %s -> %s", raw[:200], e)

    def on_pending_opened(self, raw: str) -> None:
        """ペンディング約定通知を受信し、ログ出力・ポジション管理に利用する。"""
        try:
            data = json.loads(raw)
            if data.get("type") != "pending_opened":
                return
            ticket = data.get("ticket", 0)
            symbol = data.get("symbol", "")
            order_type = data.get("order_type", "")
            lots = data.get("lots", 0.0)
            open_price = data.get("open_price", 0.0)
            open_time = data.get("open_time", "")
            logger.info(
                "ペンディング約定通知: ticket=%s symbol=%s order_type=%s lots=%s open_price=%s open_time=%s",
                ticket,
                symbol,
                order_type,
                lots,
                open_price,
                open_time,
            )
            # 必要に応じて売買結果CSVへ追記や戦略の状態更新を行う
            row = TradeResultRow(
                executed_at=open_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                symbol=symbol,
                side="BUY" if "BUY" in order_type else "SELL",
                lots=float(lots),
                price=float(open_price),
                ticket=ticket,
                status="pending_opened",
                pnl=0.0,
                memo="pending_opened",
            )
            self.append_trade_result(row)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("ペンディング約定通知パースエラー: %s -> %s", raw[:200], e)

    def append_trade_result(self, row: TradeResultRow) -> None:
        path = self._trade_result_path()
        file_exists = path.exists()
        with path.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=TRADE_RESULT_HEADER)
            if not file_exists:
                w.writeheader()
            w.writerow(row.model_dump())

    def output_pnl_summary(self, period_type: str = "daily") -> None:
        """売買結果CSVを読み、期間別に集計して損益集計CSVを出力する。"""
        if self._file_per_day:
            files = sorted(self._result_dir.glob("trade_results_*.csv"))
        else:
            files = (
                [self._result_dir / "trade_results.csv"]
                if (self._result_dir / "trade_results.csv").exists()
                else []
            )
        rows: list[TradeResultRow] = []
        for path in files:
            if not path.exists():
                continue
            with path.open(encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for line in r:
                    rows.append(
                        TradeResultRow(
                            executed_at=line.get("executed_at", ""),
                            symbol=line.get("symbol", ""),
                            side=line.get("side", "BUY"),
                            lots=float(line.get("lots", 0) or 0),
                            price=float(line.get("price", 0) or 0),
                            ticket=int(line.get("ticket", 0) or 0),
                            status=line.get("status", ""),
                            pnl=float(line.get("pnl", 0) or 0),
                            memo=line.get("memo", ""),
                        )
                    )
        if not rows:
            logger.info("売買結果が0件のため損益集計をスキップ")
            return
        # 簡易集計: 全期間で1件のサマリを出力
        total_pnl = sum(r.pnl for r in rows)
        win_count = sum(1 for r in rows if r.pnl > 0)
        loss_count = sum(1 for r in rows if r.pnl < 0)
        executed_dates = [r.executed_at[:10] for r in rows if r.executed_at]
        period_start = min(executed_dates) if executed_dates else ""
        period_end = max(executed_dates) if executed_dates else ""
        summary = PnlSummaryRow(
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            trade_count=len(rows),
            total_pnl=total_pnl,
            win_count=win_count,
            loss_count=loss_count,
        )
        out_path = (
            self._pnl_dir
            / f"pnl_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        with out_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=PNL_SUMMARY_HEADER)
            w.writeheader()
            w.writerow(summary.model_dump())
        logger.info("損益集計出力: %s", out_path)
