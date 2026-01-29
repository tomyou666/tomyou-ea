from injector import Binder, Injector

from app_server.database.db_config import (
    AsyncDBConfig,
    DBConfig,
    ProductionAsyncMySqlDBConfig,
    ProductionAsyncPostgresqlDBConfig,
    ProductionMySqlDBConfig,
    ProductionPostgresqlDBConfig,
)
from app_server.model.enum.db_type_enum import DBType
from app_server.repository.test_member_repository import MemberRepository, ProductionMemberRepository
from app_server.service.auth_service import AuthService, DebugAuthService, ProductionAuthService
from app_server.service.test_member_service import MemberService, ProductionMemberService
from app_server.share import const
from app_server.share.common_util import CommonUtil


class DI:
    """Dependency Injectionを実現する"""

    def __init__(self) -> None:
        # 依存関係を設定する関数を読み込む
        self.injector = Injector(self.__class__.config)  # type: ignore

    # 依存関係を設定するメソッド
    @classmethod
    def config(cls, binder: Binder):
        if CommonUtil.is_debug():
            # サービス
            binder.bind(interface=AuthService, to=DebugAuthService)
            binder.bind(interface=MemberService, to=ProductionMemberService)
            # # リポジトリ
            binder.bind(interface=MemberRepository, to=ProductionMemberRepository)
        else:
            # サービス
            binder.bind(interface=AuthService, to=ProductionAuthService)
            binder.bind(interface=MemberService, to=ProductionMemberService)
            # # リポジトリ
            binder.bind(interface=MemberRepository, to=ProductionMemberRepository)

    # injector.get()に引数を渡すと依存関係を解決してインスタンスを生成する
    def resolve(self, cls):
        return self.injector.get(cls)
