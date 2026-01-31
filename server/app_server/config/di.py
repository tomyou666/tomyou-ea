import zmq
from app_server.application.process_service.base import Processor
from app_server.application.process_service.tick_processor import TickProcessor
from app_server.application.trading_service.base import TradingServiceBase
from app_server.application.trading_service.trading_service import TradingService
from app_server.domain.sender.base import OrderSender
from app_server.domain.sender.mock_order_sender import MockOrderSender
from app_server.domain.sender.mt4_order_sender import Mt4OrderSender
from app_server.domain.strategy.base import Strategy
from app_server.domain.strategy.ma_crossover_strategy import MACrossoverStrategy
from app_server.infrastructure.sender.mt4_payload_sender import Mt4PayloadSender
from app_server.infrastructure.trade_result_repository.base import TradeResultRepositoryBase
from app_server.infrastructure.trade_result_repository.csv_trade_result_repository import (
    CsvTradeResultRepository,
)
from app_server.share.common_util import CommonUtil
from injector import Binder, Injector, Module, provider, singleton


class AppModule(Module):
    """Dependency Injection モジュール"""

    def __init__(self, zmq_push_socket: zmq.Socket | None = None) -> None:
        """ZeroMQ PUSH ソケットを受け取る（本番用）。デバッグモードでは不要。"""
        self._zmq_push_socket = zmq_push_socket

    def configure(self, binder: Binder) -> None:
        """単純なバインドはここで設定"""
        binder.bind(interface=Processor, to=TickProcessor)
        binder.bind(interface=Strategy, to=MACrossoverStrategy)
        binder.bind(interface=TradingServiceBase, to=TradingService)
        binder.bind(interface=TradeResultRepositoryBase, to=CsvTradeResultRepository)

    @singleton
    @provider
    def provide_order_sender(self) -> OrderSender:
        """OrderSender を provider で手動インスタンス化する。本番では payload sender を注入。"""
        if CommonUtil.is_debug():
            return MockOrderSender()
        if self._zmq_push_socket is None:
            raise RuntimeError("本番モードでは zmq_push_socket が必要です")
        payload_sender = Mt4PayloadSender(socket=self._zmq_push_socket)
        return Mt4OrderSender(payload_sender=payload_sender)


class DI:
    """Dependency Injectionを実現する"""

    def __init__(self, zmq_push_socket: zmq.Socket | None = None) -> None:
        """ZeroMQ PUSH ソケットを受け取り、Module に渡す。"""
        module = AppModule(zmq_push_socket=zmq_push_socket)
        self.injector = Injector([module])

    def resolve(self, cls):
        """injector.get() で依存関係を解決してインスタンスを生成する"""
        return self.injector.get(cls)
