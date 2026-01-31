from datetime import datetime

from app_server.model.trading import TickDto
from app_server.share.logger_util import get_logger

logger = get_logger()

# MT4送信形式: SYMBOL,BID,ASK,SPREAD,TIME 例: USDJPY,149.123,149.125,2,2025.01.29 12:00:00
TICK_TIME_FMT = "%Y.%m.%d %H:%M:%S"


class ProcessorUtil:
    """ProcessorUtilを作成するクラス."""

    TICK_TIME_FMT = "%Y.%m.%d %H:%M:%S"

    @staticmethod
    def parse_line(line: str) -> TickDto | None:
        """1行のCSVをパースして TickDto を返す。失敗時は None。"""
        line = (line or "").strip()
        if not line:
            return None
        parts = line.split(",")
        if len(parts) < 5:
            logger.warning("ティック形式不正(列不足): %s", line)
            return None
        try:
            symbol = parts[0].strip()
            bid = float(parts[1].strip())
            ask = float(parts[2].strip())
            spread = int(parts[3].strip())
            time_str = parts[4].strip()
            try:
                time_parsed = datetime.strptime(time_str, TICK_TIME_FMT)
            except ValueError:
                time_parsed = time_str  # パース失敗時は文字列のまま
            return TickDto(
                symbol=symbol,
                bid=bid,
                ask=ask,
                spread=spread,
                time=time_parsed,
            )
        except (ValueError, IndexError) as e:
            logger.warning("ティックパースエラー: %s -> %s", line, e)
            return None
