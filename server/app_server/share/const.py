import os
from pathlib import Path

from dotenv import load_dotenv


def is_debug() -> bool:
    """デバッグモードか判断する.循環参照回避のため直接isDebug関数を記述.

    Returns
    -------
        bool: true:デバッグモード

    """
    return os.getenv(IS_DEBUG) == "TRUE"


def getenv(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        msg = f"Environment variable {key} is not set."
        raise ValueError(msg)
    return value


""" 環境変数名 """
IS_DEBUG = "IS_DEBUG"

# .envファイルを読み込む
dot_env_path = None if not is_debug() else ".env.development"
load_dotenv(dot_env_path)

""" ディレクトリ """
LOG_DIR = "log/"
SETTING_DIRECTORY = "setting/"
RESOUCES_DIRECTORY = "resources.develop/" if is_debug() else "resources/"

""" ファイル名 """
SETTING_FILE = "setting.ini"
LOG_FILE = "app_server.log"

""" ファイルパス """
LOG_PATH = Path(LOG_DIR, LOG_FILE).__str__()
SETTING_PATH = Path(RESOUCES_DIRECTORY, SETTING_FILE).__str__()

""" その他 """
LOG_MAX_BYTE = 1000000
