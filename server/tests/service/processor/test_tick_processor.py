"""加工部テスト（設計書 10.1）"""

import pytest

from app_server.model.trading import TickDto
from app_server.service.processor.tick_processor import TickProcessor


def test_tick_processor_parse_valid_csv() -> None:
    """有効なティックCSVをパースすると TickDto が返る"""
    proc = TickProcessor()
    raw = "USDJPY,149.123,149.125,2,2025.01.29 12:00:00"
    result = proc.parse(raw)
    assert result is not None
    assert isinstance(result, TickDto)
    assert result.symbol == "USDJPY"
    assert result.bid == 149.123
    assert result.ask == 149.125
    assert result.spread == 2
    assert str(result.time) == "2025-01-29 12:00:00"


def test_tick_processor_parse_invalid_returns_none() -> None:
    """列不足のCSVは None を返す"""
    proc = TickProcessor()
    assert proc.parse("USDJPY,149.123") is None
    assert proc.parse("") is None


def test_tick_processor_parse_list_returns_none() -> None:
    """リストを渡した場合は None（TickProcessor は1件用）"""
    proc = TickProcessor()
    assert proc.parse(["USDJPY,149.123,149.125,2,2025.01.29 12:00:00"]) is None
