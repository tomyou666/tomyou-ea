"""リアルタイムティック用加工部"""

from app_server.application.process_service.base import Processor
from app_server.application.process_service.util import ProcessorUtil
from app_server.models.trading import TickDto
from app_server.share.logger_util import get_logger

logger = get_logger()

# MT4送信形式: SYMBOL,BID,ASK,SPREAD,TIME 例: USDJPY,149.123,149.125,2,2025.01.29 12:00:00
TICK_TIME_FMT = "%Y.%m.%d %H:%M:%S"


class TickProcessor(Processor):
    """ZeroMQ から受信した 1 件の CSV 文字列を TickDto に変換する（リアルタイム用）"""

    def parse(self, raw: str | list[str]) -> TickDto | list[TickDto] | None:
        if isinstance(raw, list):
            return None
        return ProcessorUtil.parse_line(raw)
