import zmq
from app_server.domain.core_logic.base import CoreLogic
from app_server.domain.core_logic.trading_core import TradingCore
from app_server.domain.order.base import OrderSender
from app_server.domain.order.mock_order_sender import MockOrderSender
from app_server.domain.order.mt4_order_sender import Mt4OrderSender
from app_server.domain.processor.base import Processor
from app_server.domain.processor.tick_processor import TickProcessor
from app_server.domain.strategy.base import Strategy
from app_server.domain.strategy.ma_crossover_strategy import MACrossoverStrategy
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
        binder.bind(interface=CoreLogic, to=TradingCore)

    @singleton
    @provider
    def provide_order_sender(self) -> OrderSender:
        """OrderSender を provider で手動インスタンス化する。"""
        if CommonUtil.is_debug():
            return MockOrderSender()
        else:
            if self._zmq_push_socket is None:
                raise RuntimeError("本番モードでは zmq_push_socket が必要です")
            return Mt4OrderSender(socket=self._zmq_push_socket)


class DI:
    """Dependency Injectionを実現する"""

    def __init__(self, zmq_push_socket: zmq.Socket | None = None) -> None:
        """ZeroMQ PUSH ソケットを受け取り、Module に渡す。"""
        module = AppModule(zmq_push_socket=zmq_push_socket)
        self.injector = Injector([module])

    def resolve(self, cls):
        """injector.get() で依存関係を解決してインスタンスを生成する"""
        return self.injector.get(cls)
        return self.injector.get(cls)
