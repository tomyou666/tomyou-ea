from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TokenSrc(BaseModel):
    """トークンの生成用の情報

    Attributes
    ----------
        sub (str): トークンのサブジェクトを表す文字列
        exp (datetime): トークンの有効期限を表す整数

    """

    sub: str
    exp: datetime | None = None


class Token(BaseModel):
    """トークン

    Attributes
    ----------
        access_token (str): アクセストークン
        token_type (str): トークンの種類 default to "Bearer"

    """

    access_token: str
    token_type: str = "Bearer"
