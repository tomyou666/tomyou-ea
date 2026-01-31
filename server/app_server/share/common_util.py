import os
import subprocess

from app_server.models.trading import Signal, SignalResult, TickDto, TradeResultRow
from app_server.share import const
from app_server.share.logger_util import get_logger

# ロガー取得
logger = get_logger()


class CommonUtil:
    """共通処理を作成するクラス."""

    @staticmethod
    def is_debug() -> bool:
        """デバッグモードか判断する.

        Returns
        -------
            bool: true:デバッグモード

        """
        return os.getenv(const.IS_DEBUG) == "TRUE"

    @staticmethod
    def execute_cmd(cmd: list[str]) -> tuple[bool, str]:
        """指定されたコマンドを実行し、その出力を返す関数.

        Args:
        ----
            cmd (List[str]): 実行するコマンドのリスト

        Returns:
        -------
            tuple[bool, str]: (コマンド成功可否, コマンドの出力)

        """
        try:
            # コマンドを実行し、結果を取得する
            logger.info(f"[CMD RUN]: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return (True, result.stdout)
        except subprocess.CalledProcessError as e:
            logger.exception(e)
            return (False, f"Error executing command: {e}\n{e.stderr}")


def signal_to_trade_result_row(
    result: Signal | SignalResult,
    tick: TickDto,
    ticket: int = 1,
    status: str = "SUCCESS",
    pnl: float = 0.0,
    memo: str = "backtest",
) -> TradeResultRow:
    """on_tick の戻り値（Signal | SignalResult）と TickDto から TradeResultRow を組み立てる。"""
    signal = result.signal if isinstance(result, SignalResult) else result
    side = signal.value if hasattr(signal, "value") else str(signal)
    lots = result.lots if isinstance(result, SignalResult) else 0.01
    price = tick.ask if side == "BUY" else tick.bid
    if isinstance(tick.time, str):
        executed_at = tick.time.replace(".", "-", 2)[:19]  # "2025.01.29 12:00:00" -> "2025-01-29 12:00:00"
    else:
        executed_at = tick.time.strftime("%Y-%m-%d %H:%M:%S")
    return TradeResultRow(
        executed_at=executed_at,
        symbol=tick.symbol,
        side=side,  # type: ignore[arg-type]
        lots=lots,
        price=price,
        ticket=ticket,
        status=status,
        pnl=pnl,
        memo=memo,
    )
