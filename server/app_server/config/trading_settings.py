"""売買・ZeroMQ 用設定読み込み。setting.ini が無い場合は既定値を使用。"""

import configparser
import os
from pathlib import Path

DEFAULT_ZMQ_RECV_PORT = 5555
DEFAULT_ZMQ_SEND_PORT = 5556
DEFAULT_TRADE_RESULT_DIR = "trade_results"
DEFAULT_PNL_SUMMARY_DIR = "pnl_summary"


def _setting_path() -> Path:
    cwd = Path.cwd()
    is_dev = os.getenv("IS_DEBUG") == "TRUE"
    sub = "resources.develop" if is_dev else "resources"
    return cwd / sub / "setting.ini"


def _get(div: str, param: str, default: str) -> str:
    path = _setting_path()
    if not path.exists():
        return default
    try:
        cfg = configparser.ConfigParser()
        cfg.read(path, encoding="utf-8")
        if div in cfg and param in cfg[div]:
            return cfg[div][param].strip()
    except Exception:
        pass
    return default


def get_zmq_recv_port() -> int:
    try:
        return int(_get("ZMQ", "recv_port", str(DEFAULT_ZMQ_RECV_PORT)))
    except ValueError:
        return DEFAULT_ZMQ_RECV_PORT


def get_zmq_send_port() -> int:
    try:
        return int(_get("ZMQ", "send_port", str(DEFAULT_ZMQ_SEND_PORT)))
    except ValueError:
        return DEFAULT_ZMQ_SEND_PORT


def get_trade_result_dir() -> str:
    return _get("TRADING", "trade_result_dir", DEFAULT_TRADE_RESULT_DIR)


def get_pnl_summary_dir() -> str:
    return _get("TRADING", "pnl_summary_dir", DEFAULT_PNL_SUMMARY_DIR)


def get_trade_result_file_per_day() -> bool:
    """True: trade_results_YYYYMMDD.csv, False: trade_results.csv"""
    return _get("TRADING", "result_file_per_day", "true").lower() in ("true", "1", "yes")
