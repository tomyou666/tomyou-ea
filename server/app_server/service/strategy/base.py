"""戦略部の抽象基底クラス（設計書 4.3）"""

from abc import ABCMeta, abstractmethod
from typing import Any

from app_server.model.trading import Signal, SignalResult, TickDto


class Strategy(metaclass=ABCMeta):
    """加工済みデータからシグナルを返す戦略の基底クラス"""

    @abstractmethod
    def next(self, tick: TickDto, context: Any | None = None) -> Signal | SignalResult:
        """1 ティックを受け取り、シグナル（買い/売り/ホールド）を返す。

        Args:
            tick: 加工済みティック
            context: オプションのコンテキスト（バックテスト用など）

        Returns:
            Signal または SignalResult
        """
        raise NotImplementedError
