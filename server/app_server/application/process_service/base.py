"""加工部の抽象基底クラス"""

from abc import ABCMeta, abstractmethod

from app_server.models.trading import TickDto


class Processor(metaclass=ABCMeta):
    """受信した生データを TickDto に変換する加工部の基底クラス"""

    @abstractmethod
    def parse(self, raw: str | list[str]) -> TickDto | list[TickDto] | None:
        """生データを TickDto（またはリスト）に変換する。

        Args:
            raw: 1件のCSV文字列（リアルタイム）または複数行（一括）

        Returns:
            TickDto または TickDto のリスト。パース失敗時は None。

        """
        raise NotImplementedError
