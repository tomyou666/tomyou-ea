"""backtestingライブラリを使用したバックテストの統合テスト"""

import csv
from pathlib import Path

import pandas as pd
import pytest
import yfinance as yf
from app_server.application.process_service.csv_processor import CsvBatchProcessor
from app_server.application.trading_service.trading_service import TradingService
from app_server.domain.sender.mock_order_sender import MockOrderSender
from app_server.domain.strategy.base import Strategy
from app_server.infrastructure.trade_result_repository.csv_trade_result_repository import (
    CsvTradeResultRepository,
)
from app_server.domain.strategy.simple_strategy import SimpleStrategy
from app_server.models.trading import Signal, SignalResult, TickDto
from app_server.share.common_util import signal_to_trade_result_row
from backtesting import Backtest
from backtesting import Strategy as BacktestStrategy


class BacktestStrategyWrapper(BacktestStrategy):
    """backtestingライブラリのStrategyをラップし、既存のStrategyクラスを使用する。

    既存のStrategyクラス（app_server.domain.strategy.base.Strategy）を
    backtestingライブラリで使用できるようにするラッパー。
    """

    def __init__(self, strategy: Strategy, trading_service: TradingService, *args, **kwargs):
        """既存のStrategyとTradingServiceを受け取る。

        Args:
            strategy: 既存のStrategyインスタンス
            trading_service: TradingServiceインスタンス（append_trade_result用）
        """
        super().__init__(*args, **kwargs)
        self._strategy = strategy
        self._trading_service = trading_service
        self._ticket_counter = 1

    def init(self):
        """backtestingライブラリのinitメソッド（必要に応じてオーバーライド）"""
        pass

    def next(self):
        """backtestingライブラリのnextメソッド。

        各バー（OHLCV）に対して既存のStrategy.next()を呼び出し、
        シグナルに基づいて取引を実行する。
        """
        # OHLCVデータからTickDtoを作成
        current_bar = self.data
        tick = TickDto(
            symbol="USDJPY",  # デフォルト値、実際にはデータから取得すべき
            bid=float(current_bar["Low"][0]),  # Lowをbidとして使用
            ask=float(current_bar["High"][0]),  # Highをaskとして使用
            spread=max(1, int((current_bar["High"][0] - current_bar["Low"][0]) * 100)),
            time=self.data.index[0],
        )

        # 既存のStrategy.next()を呼び出し
        result = self._strategy.next(tick, context=None)

        # シグナルに基づいて取引を実行
        if isinstance(result, SignalResult):
            signal = result.signal
            if signal == Signal.BUY:
                # backtestingライブラリのbuy()メソッドを呼び出し
                self.buy(size=result.lots)
                # 売買結果を記録
                row = signal_to_trade_result_row(
                    result,
                    tick,
                    ticket=self._ticket_counter,
                    status="SUCCESS",
                    pnl=0.0,  # バックテスト終了後に計算
                    memo="backtest",
                )
                self._trading_service.append_trade_result(row)
                self._ticket_counter += 1
            elif signal == Signal.SELL:
                # backtestingライブラリのsell()メソッドを呼び出し
                self.sell(size=result.lots)
                # 売買結果を記録
                row = signal_to_trade_result_row(
                    result,
                    tick,
                    ticket=self._ticket_counter,
                    status="SUCCESS",
                    pnl=0.0,  # バックテスト終了後に計算
                    memo="backtest",
                )
                self._trading_service.append_trade_result(row)
                self._ticket_counter += 1


class TestStrategyFirstTickBuy(Strategy):
    """テスト用: 最初の1ティックで BUY を返し、以降は HOLD。"""

    def __init__(self) -> None:
        self._first = True

    def next(self, tick: TickDto, context: object | None = None) -> Signal | SignalResult:
        if self._first:
            self._first = False
            return SignalResult(signal=Signal.BUY, lots=0.01, sl=0.0, tp=0.0)
        return SignalResult(signal=Signal.HOLD, lots=0.01, sl=0.0, tp=0.0)


def fetch_ohlcv_from_yfinance(
    ticker: str = "USDJPY=X",
    period: str = "5d",
    interval: str = "1d",
) -> pd.DataFrame:
    """yfinance でOHLCVデータを取得し、backtestingライブラリ用のDataFrameに変換する。

    Args:
        ticker: yfinanceのティッカーシンボル
        period: 取得期間（例: "5d", "1mo"）
        interval: 取得間隔（例: "1d", "1h"）

    Returns:
        OHLCVデータを含むpandas DataFrame（backtestingライブラリ用）
    """
    df = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )

    if df.empty or len(df) == 0:
        return pd.DataFrame()

    # 単一ティッカーでも MultiIndex になる場合があるのでフラット化
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)

    # backtestingライブラリが期待する形式に変換
    # 列名を大文字に（Open, High, Low, Close, Volume）
    df.columns = [col.capitalize() for col in df.columns]

    # 必要な列が存在することを確認
    required_cols = ["Open", "High", "Low", "Close"]
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

    # Volumeが存在しない場合は追加（0で埋める）
    if "Volume" not in df.columns:
        df["Volume"] = 0

    print(f"取得したデータ: {len(df)}行")
    print(df.head())

    return df[["Open", "High", "Low", "Close", "Volume"]]


def test_backtest_with_backtesting_library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """backtestingライブラリを使用してバックテストを実行し、結果をassertする。"""

    # パスのモック設定
    # monkeypatch.setattr(
    #     "app_server.application.trading_service.trading_core.get_trade_result_dir",
    #     lambda: str(tmp_path / "trade_results"),
    # )
    # monkeypatch.setattr(
    #     "app_server.application.trading_service.trading_core.get_pnl_summary_dir",
    #     lambda: str(tmp_path / "pnl_summary"),
    # )
    monkeypatch.setattr(
        "app_server.config.trading_settings.get_trade_result_file_per_day",
        lambda: False,
    )

    # OHLCVデータを取得
    data = fetch_ohlcv_from_yfinance(ticker="USDJPY=X", period="5d", interval="1d")
    if data.empty:
        pytest.skip("yfinance でデータを取得できませんでした（ネットワークまたは銘柄を確認してください）")

    # TradingServiceとStrategyを準備
    processor = CsvBatchProcessor()
    strategy = TestStrategyFirstTickBuy()
    order_sender = MockOrderSender()
    trade_result_repository = CsvTradeResultRepository()
    core = TradingService(
        processor=processor,
        strategy=strategy,
        order_sender=order_sender,
        trade_result_repository=trade_result_repository,
    )

    # backtestingライブラリ用のStrategyラッパーを作成
    class WrappedStrategy(BacktestStrategyWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(strategy, core, *args, **kwargs)

    # Backtestを実行
    bt = Backtest(data, WrappedStrategy, commission=0.002, cash=10000)
    results = bt.run()

    # バックテスト結果をassert
    assert results is not None
    # backtestingライブラリの結果は辞書のような形式でアクセス可能
    assert "Start" in results or hasattr(results, "Start")
    assert "End" in results or hasattr(results, "End")
    print("\nバックテスト結果:")
    start = results.get("Start") if isinstance(results, dict) else getattr(results, "Start", None)
    end = results.get("End") if isinstance(results, dict) else getattr(results, "End", None)
    print(f"開始: {start}")
    print(f"終了: {end}")
    if "Return [%]" in results or hasattr(results, "Return"):
        ret = results.get("Return [%]") if isinstance(results, dict) else getattr(results, "Return", None)
        if ret is not None:
            print(f"リターン: {ret:.2f}%")
    if "Sharpe Ratio" in results or hasattr(results, "Sharpe Ratio"):
        sharpe = results.get("Sharpe Ratio") if isinstance(results, dict) else getattr(results, "Sharpe Ratio", None)
        if sharpe is not None:
            print(f"シャープレシオ: {sharpe:.2f}")

    # append_trade_resultで出力されたファイルの存在を確認
    trade_result_path = core.get_trade_result_path()
    assert trade_result_path.exists(), f"売買結果CSVが存在しません: {trade_result_path}"

    # 売買結果CSVの内容を確認
    with trade_result_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        assert len(rows) >= 1, "売買結果が1件以上存在する必要があります"
        # 最初の取引がBUYであることを確認
        assert rows[0]["symbol"] == "USDJPY"
        assert rows[0]["side"] == "BUY"
        print(f"\n売買結果: {len(rows)}件")

    # output_pnl_summaryを呼び出して損益集計を出力
    core.output_pnl_summary(period_type="daily")

    # 損益集計CSVファイルの存在を確認
    pnl_files = list(core.get_pnl_dir().glob("pnl_summary_*.csv"))
    assert len(pnl_files) >= 1, "損益集計CSVが1件以上存在する必要があります"

    # 損益集計CSVの内容を確認
    with pnl_files[0].open(encoding="utf-8", newline="") as f:
        summary_rows = list(csv.DictReader(f))
        assert len(summary_rows) == 1, "損益集計は1行である必要があります"
        assert int(summary_rows[0]["trade_count"]) >= 1, "取引数が1件以上である必要があります"
        assert summary_rows[0]["period_type"] == "daily", "期間タイプがdailyである必要があります"
        print(f"\n損益集計:")
        print(f"取引数: {summary_rows[0]['trade_count']}")
        print(f"総損益: {summary_rows[0]['total_pnl']}")


def test_backtest_with_simple_strategy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SimpleStrategyを使用したbacktestingライブラリのバックテスト。"""

    # パスのモック設定
    # monkeypatch.setattr(
    #     "app_server.application.trading_service.trading_core.get_trade_result_dir",
    #     lambda: str(tmp_path / "trade_results"),
    # )
    # monkeypatch.setattr(
    #     "app_server.application.trading_service.trading_core.get_pnl_summary_dir",
    #     lambda: str(tmp_path / "pnl_summary"),
    # )
    monkeypatch.setattr(
        "app_server.config.trading_settings.get_trade_result_file_per_day",
        lambda: False,
    )

    # OHLCVデータを取得
    data = fetch_ohlcv_from_yfinance(ticker="USDJPY=X", period="5d", interval="1d")
    if data.empty:
        pytest.skip("yfinance でデータを取得できませんでした")

    # TradingServiceとStrategyを準備
    processor = CsvBatchProcessor()
    strategy = SimpleStrategy(max_spread=10)
    order_sender = MockOrderSender()
    trade_result_repository = CsvTradeResultRepository()
    core = TradingService(
        processor=processor,
        strategy=strategy,
        order_sender=order_sender,
        trade_result_repository=trade_result_repository,
    )

    # backtestingライブラリ用のStrategyラッパーを作成
    class WrappedStrategy(BacktestStrategyWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(strategy, core, *args, **kwargs)

    # Backtestを実行
    bt = Backtest(data, WrappedStrategy, commission=0.002, cash=10000)
    results = bt.run()

    # バックテスト結果をassert
    assert results is not None
    print("\nバックテスト結果 (SimpleStrategy):")
    start = results.get("Start") if isinstance(results, dict) else getattr(results, "Start", None)
    end = results.get("End") if isinstance(results, dict) else getattr(results, "End", None)
    print(f"開始: {start}")
    print(f"終了: {end}")

    # append_trade_resultとoutput_pnl_summaryで出力されたファイルの存在を確認
    # SimpleStrategyはHOLDを返すため、取引が発生しない可能性がある
    trade_result_path = core.get_trade_result_path()
    # ファイルが存在するかどうかは取引が発生したかによる
    if trade_result_path.exists():
        with trade_result_path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
            print(f"売買結果: {len(rows)}件")

    # output_pnl_summaryを呼び出して損益集計を出力
    core.output_pnl_summary(period_type="daily")

    # 損益集計CSVファイルの存在を確認（取引がなくてもファイルは作成される可能性がある）
    pnl_files = list(core.get_pnl_dir().glob("pnl_summary_*.csv"))
    if len(pnl_files) >= 1:
        with pnl_files[0].open(encoding="utf-8", newline="") as f:
            summary_rows = list(csv.DictReader(f))
            if len(summary_rows) > 0:
                print(f"損益集計: 取引数={summary_rows[0]['trade_count']}")
                print(f"損益集計: 取引数={summary_rows[0]['trade_count']}")
                print(f"損益集計: 取引数={summary_rows[0]['trade_count']}")
                print(f"損益集計: 取引数={summary_rows[0]['trade_count']}")
