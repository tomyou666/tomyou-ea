"""本番用トレード処理の制御：ZeroMQ 受信と連携、売買結果CSV・損益集計CSV"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app_server.application.process_service.base import Processor
from app_server.application.trading_service.base import TradingServiceBase
from app_server.domain.sender.base import OrderSender
from app_server.domain.strategy.base import Strategy
from app_server.infrastructure.trade_result_repository.base import TradeResultRepositoryBase
from app_server.models.trading import OrderResult, Signal, SignalResult, TickDto, TradeResultRow
from app_server.share.logger_util import get_logger
from injector import inject

logger = get_logger()


@inject
@dataclass
class TradingService(TradingServiceBase):
    """加工部・戦略部・命令部を組み合わせ、受信→加工→戦略→命令とCSV記録・集計を行う。

    @inject により Processor, Strategy, OrderSender, TradeResultRepositoryBase が DI で注入される。
    """

    processor: Processor
    strategy: Strategy
    order_sender: OrderSender
    trade_result_repository: TradeResultRepositoryBase

    def get_trade_result_path(self) -> Path:
        """売買結果CSVの出力パスを返す（テスト・呼び出し元用）。"""
        return self.trade_result_repository.get_trade_result_path()

    def get_result_dir(self) -> Path:
        """売買結果CSVの出力ディレクトリを返す（テスト・呼び出し元用）。"""
        return self.trade_result_repository.get_result_dir()

    def get_pnl_dir(self) -> Path:
        """損益集計CSVの出力ディレクトリを返す（テスト・呼び出し元用）。"""
        return self.trade_result_repository.get_pnl_dir()

    def on_tick(self, raw: str) -> Signal | SignalResult | None:
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
            cmd = self.order_sender.build_order_command(out, symbol, lots=lots, price=price, sl=sl, tp=tp)
            if self.order_sender.send_order(cmd):
                logger.info("シグナルに基づき注文送信: %s %s", signal, symbol)
            return out
        except Exception as e:
            logger.warning("戦略処理中の例外（ティックスキップ）: %s", e)
            return None

    def on_order_result(self, raw: str) -> None:
        try:
            data = json.loads(raw)
            request_id = data.get("request_id", "")
            status = data.get("status", "")
            if status == "FAILED":
                code = data.get("code", 0)
                message = data.get("message", "")
                row = TradeResultRow(
                    executed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    symbol="",
                    side="BUY",
                    lots=0.0,
                    price=0.0,
                    ticket=0,
                    status="FAILED",
                    pnl=0.0,
                    memo=f"code={code} {message}",
                )
                self.trade_result_repository.append_trade_result(row)
                logger.warning(
                    "注文結果失敗受信: request_id=%s code=%s message=%s",
                    request_id,
                    code,
                    message,
                )
                return
            if data.get("type") != "order_result":
                return
            res = OrderResult(
                type="order_result",
                request_id=request_id,
                ticket=data.get("ticket", 0),
                status=status,
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
            self.trade_result_repository.append_trade_result(row)
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
            self.trade_result_repository.append_trade_result(row)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("ペンディング約定通知パースエラー: %s -> %s", raw[:200], e)

    def append_trade_result(self, row: TradeResultRow) -> None:
        """売買結果を1行追記する（infrastructure の repository に委譲）。"""
        self.trade_result_repository.append_trade_result(row)

    def output_pnl_summary(self, period_type: str = "daily") -> None:
        """損益集計を出力する（infrastructure の repository に委譲）。"""
        self.trade_result_repository.output_pnl_summary(period_type=period_type)
        self.trade_result_repository.output_pnl_summary(period_type=period_type)
