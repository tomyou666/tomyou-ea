import os
import subprocess

from sqlalchemy.orm import DeclarativeBase

from app_server.share import const
from app_server.share.logger_util import get_logger

# ロガー取得
logger = get_logger()


class CommonUtil:
    """共通処理を作成するクラス."""

    @staticmethod
    def is_debug() -> bool:
        """デバッグモードか判断する.

        Returns
        -------
            bool: true:デバッグモード

        """
        return os.getenv(const.IS_DEBUG) == "TRUE"

    @staticmethod
    def to_dict(model: DeclarativeBase, ignore_null=False) -> dict:
        """sqlオブジェクトをdict型に変換する.

        Args:
        ----
            model (Base): モデルオブジェクト
            ignore_null (bool, optional): nullを無視するか. Defaults to False.

        Returns:
        -------
            dict: dict型のsqlオブジェクト

        """
        return {
            key: value
            for key, value in model.__dict__.items()
            if key != "_sa_instance_state" and (not ignore_null or value is not None)
        }

    @staticmethod
    def execute_cmd(cmd: list[str]) -> tuple[bool, str]:
        """指定されたコマンドを実行し、その出力を返す関数.

        Args:
        ----
            cmd (List[str]): 実行するコマンドのリスト

        Returns:
        -------
            tuple[bool, str]: (コマンド成功可否, コマンドの出力)

        """
        try:
            # コマンドを実行し、結果を取得する
            logger.info(f"[CMD RUN]: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return (True, result.stdout)
        except subprocess.CalledProcessError as e:
            logger.exception(e)
            return (False, f"Error executing command: {e}\n{e.stderr}")
