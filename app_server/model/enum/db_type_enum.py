from enum import StrEnum, auto


class DBType(StrEnum):
    """DBの種類を表すEnum"""

    POSTGRESQL = auto()
    MYSQL = auto()
