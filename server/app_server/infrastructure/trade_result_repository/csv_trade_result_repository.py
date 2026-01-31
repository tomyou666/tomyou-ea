"""売買結果・損益集計の CSV 永続化実装（infrastructure 層）"""

import csv
from datetime import datetime
from pathlib import Path

from app_server.config.trading_settings import get_pnl_summary_dir, get_trade_result_dir, get_trade_result_file_per_day
from app_server.infrastructure.trade_result_repository.base import TradeResultRepositoryBase
from app_server.models.trading import PnlSummaryRow, TradeResultRow
from app_server.share.logger_util import get_logger

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


class CsvTradeResultRepository(TradeResultRepositoryBase):
    """売買結果CSV・損益集計CSV をファイルに書き出す実装"""

    def __init__(self) -> None:
        self._result_dir = Path(get_trade_result_dir())
        self._pnl_dir = Path(get_pnl_summary_dir())
        self._file_per_day = get_trade_result_file_per_day()
        self._result_dir.mkdir(parents=True, exist_ok=True)
        self._pnl_dir.mkdir(parents=True, exist_ok=True)

    def _trade_result_path(self) -> Path:
        if self._file_per_day:
            return self._result_dir / f"trade_results_{datetime.now().strftime('%Y%m%d')}.csv"
        return self._result_dir / "trade_results.csv"

    def get_trade_result_path(self) -> Path:
        """売買結果CSVの出力パスを返す（テスト・呼び出し元用）。"""
        return self._trade_result_path()

    def get_result_dir(self) -> Path:
        """売買結果CSVの出力ディレクトリを返す。"""
        return self._result_dir

    def get_pnl_dir(self) -> Path:
        """損益集計CSVの出力ディレクトリを返す。"""
        return self._pnl_dir

    def append_trade_result(self, row: TradeResultRow) -> None:
        path = self._trade_result_path()
        file_exists = path.exists()
        with path.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=TRADE_RESULT_HEADER)
            if not file_exists:
                w.writeheader()
            w.writerow(row.model_dump())

    def output_pnl_summary(self, period_type: str = "daily") -> None:
        if self._file_per_day:
            files = sorted(self._result_dir.glob("trade_results_*.csv"))
        else:
            files = (
                [self._result_dir / "trade_results.csv"] if (self._result_dir / "trade_results.csv").exists() else []
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
        out_path = self._pnl_dir / f"pnl_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=PNL_SUMMARY_HEADER)
            w.writeheader()
            w.writerow(summary.model_dump())
        logger.info("損益集計出力: %s", out_path)
