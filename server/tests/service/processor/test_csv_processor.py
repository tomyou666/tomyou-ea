"""一括CSV加工部テスト（バックテスト用 CSV → TickDto）"""

from pathlib import Path

import pytest
from app_server.domain.processor.csv_processor import CsvBatchProcessor
from app_server.model.trading import TickDto


def test_csv_batch_processor_parse_single_line() -> None:
    """1行のCSV文字列を渡すと TickDto が1件返る"""
    proc = CsvBatchProcessor()
    raw = "USDJPY,149.123,149.125,2,2025.01.29 12:00:00"
    result = proc.parse(raw)
    assert result is not None
    assert isinstance(result, TickDto)
    assert result.symbol == "USDJPY"
    assert result.bid == 149.123
    assert result.ask == 149.125


def test_csv_batch_processor_parse_list_of_lines() -> None:
    """複数行のリストを渡すと TickDto のリストが返る"""
    proc = CsvBatchProcessor()
    raw = [
        "USDJPY,149.123,149.125,2,2025.01.29 12:00:00",
        "USDJPY,149.124,149.126,2,2025.01.29 12:01:00",
        "EURUSD,1.0800,1.0802,2,2025.01.29 12:02:00",
    ]
    result = proc.parse(raw)
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(t, TickDto) for t in result)
    assert result[0].symbol == "USDJPY" and result[0].bid == 149.123
    assert result[1].symbol == "USDJPY" and result[1].bid == 149.124
    assert result[2].symbol == "EURUSD" and result[2].bid == 1.08


def test_csv_batch_processor_parse_list_with_invalid_line_skipped() -> None:
    """不正行はスキップされ、有効な行だけ返る"""
    proc = CsvBatchProcessor()
    raw = [
        "USDJPY,149.123,149.125,2,2025.01.29 12:00:00",
        "short",
        "USDJPY,149.124,149.126,2,2025.01.29 12:01:00",
    ]
    result = proc.parse(raw)
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].bid == 149.123 and result[1].bid == 149.124


def test_csv_batch_processor_parse_list_all_invalid_returns_none() -> None:
    """すべて不正な場合は None"""
    proc = CsvBatchProcessor()
    result = proc.parse(["bad", "", "x,y"])
    assert result is None


def test_csv_batch_processor_iter_from_file(tmp_path: Path) -> None:
    """CSVファイルから1件ずつ TickDto が yield される"""
    csv_file = tmp_path / "ticks.csv"
    csv_file.write_text(
        "# comment\nUSDJPY,149.123,149.125,2,2025.01.29 12:00:00\nUSDJPY,149.124,149.126,2,2025.01.29 12:01:00\n\n",
        encoding="utf-8",
    )
    proc = CsvBatchProcessor()
    ticks = list(proc._iter_from_file(csv_file))
    assert len(ticks) == 2
    assert ticks[0].symbol == "USDJPY" and ticks[0].bid == 149.123
    assert ticks[1].bid == 149.124


def test_csv_batch_processor_iter_from_file_not_exists() -> None:
    """存在しないファイルの場合は空で終了"""
    proc = CsvBatchProcessor()
    ticks = list(proc._iter_from_file("/nonexistent/ticks.csv"))
    assert len(ticks) == 0
    assert len(ticks) == 0
