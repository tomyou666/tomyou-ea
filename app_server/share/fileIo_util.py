import configparser
from pathlib import Path

import pandas as pd

from app_server.share.logger_util import get_logger
from app_server.share.my_exception import IniFileReadError

# ロガー取得
logger = get_logger()


class FileIoUtil:
    """ファイルの入出力に関する処理を作成するクラス."""

    @staticmethod
    def get_properties(file: str, div: str, param: str) -> str:
        """_summary_.

        Args:
        ----
            file (str): ファイルパス
            div (str): 区分 div=Noneの場合はparam値のみをキーとして設定値を取得する
            param (str): プロパティ名

        Raises:
        ------
            FileNotFoundError: ファイルがない
            IniFileReadError: キーが正しくない

        Returns:
        -------
            str: 設定値読み取り, 項目存在しないor設定ファイル存在しない: None.

        """
        ret_val = ""
        if not Path(file).exists():
            msg = f"{file} is not exist."
            raise FileNotFoundError(msg)

        # 設定ファイル読み込み
        config_ini = configparser.ConfigParser()
        config_ini.read(file, encoding="utf-8")

        ret_val = config_ini[param] if div is None else config_ini[div][param]
        # エラーチェック
        if ret_val == "":
            msg = f"FileName: {file}, param: {param} is invalid"
            raise IniFileReadError(msg)
        # get parameter
        return config_ini[div][param]

    @staticmethod
    def read_csv(file_path, delimiter=",", encoding="utf-8", header=None) -> pd.DataFrame:
        """CSVファイルをDataFrameに読み込む関数。

        パラメータ:
        - file_path (str): CSVファイルのパス。
        - delimiter (str): CSVファイルで使用される区切り文字。デフォルトは ','。
        - encoding (str): CSVファイルのエンコーディング。デフォルトは 'utf-8'。

        戻り値:
        - DataFrame: CSVデータを含むDataFrame。
        """
        data = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, header=header)
        return data
