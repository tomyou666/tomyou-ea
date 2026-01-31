"""売買結果・損益集計の永続化の抽象基底クラス"""

from abc import ABCMeta, abstractmethod
from pathlib import Path

from app_server.models.trading import TradeResultRow


class TradeResultRepositoryBase(metaclass=ABCMeta):
    """売買結果の追記・損益集計出力のインターフェース"""

    @abstractmethod
    def append_trade_result(self, row: TradeResultRow) -> None:
        """売買結果を1行追記する。"""
        raise NotImplementedError

    @abstractmethod
    def output_pnl_summary(self, period_type: str = "daily") -> None:
        """売買結果CSVを読み、期間別に集計して損益集計CSVを出力する。"""
        raise NotImplementedError

    @abstractmethod
    def get_trade_result_path(self) -> Path:
        """売買結果CSVの出力パスを返す（テスト・呼び出し元用）。"""
        raise NotImplementedError

    @abstractmethod
    def get_result_dir(self) -> Path:
        """売買結果CSVの出力ディレクトリを返す。"""
        raise NotImplementedError

    @abstractmethod
    def get_pnl_dir(self) -> Path:
        """損益集計CSVの出力ディレクトリを返す。"""
        raise NotImplementedError
