"""一括CSV用加工部（バックテスト用、設計書 4.2, 6.3）"""

from collections.abc import Iterator
from pathlib import Path

from app_server.model.trading import TickDto
from app_server.service.processor.base import Processor
from app_server.service.processor.util import ProcessorUtil
from app_server.share.logger_util import get_logger

from server.app_server.service.processor.tick_processor import TickProcessor

logger = get_logger()


class CsvBatchProcessor(Processor):
    """CSV ファイルを 1 行ずつ読み、TickDto に変換して yield する（バックテスト用）"""

    def __init__(self) -> None:
        self._tick_processor: Processor = TickProcessor()

    def parse(self, raw: str | list[str]) -> TickDto | list[TickDto] | None:
        """リストの場合は全行をパースしてリストで返す。文字列の場合は1行として扱う。"""
        if isinstance(raw, list):
            result: list[TickDto] = []
            for line in raw:
                dto = ProcessorUtil.parse_line(line if isinstance(line, str) else str(line))
                if dto is not None:
                    result.append(dto)
            return result if result else None
        return self._tick_processor.parse(raw)

    def _iter_from_file(self, file_path: str | Path) -> Iterator[TickDto]:
        """CSV ファイルを 1 行ずつ読み、TickDto を yield する。"""
        path = Path(file_path)
        if not path.exists():
            logger.warning("CSVファイルが存在しません: %s", path)
            return
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                dto = ProcessorUtil.parse_line(line)
                if dto is not None:
                    yield dto
