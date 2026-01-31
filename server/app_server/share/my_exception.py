# 独自の例外を作成する


class FastApiError(Exception):
    """FastApiエラー."""


class IniFileReadError(Exception):
    """Iniファイル読み取りエラー."""


class ClassFieldMissingError(Exception):
    """クラスフィールド不足エラー."""


class UnicornException(Exception):  # noqa: N818
    """エラーハンドラ.

    Args:
    ----
        Exception (Exception): 例外

    """

    def __init__(self, name: str):
        self.name = name


class Mt4RequestTimeoutError(Exception):
    """応答がタイムアウトまたはリトライ上限に達した場合のエラー（order 層で送出）"""

    pass
