"""命令部モックテスト（設計書 10.4）"""

import pytest

from app_server.model.trading import OrderCommand
from app_server.service.order.mock_order_sender import MockOrderSender


def test_mock_order_sender_records_commands() -> None:
    """送信した OrderCommand が sent_commands に記録される"""
    sender = MockOrderSender()
    cmd = OrderCommand(
        action="ORDER",
        symbol="USDJPY",
        type="BUY",
        lots=0.01,
        price=0.0,
        sl=0.0,
        tp=0.0,
    )
    assert sender.send_order(cmd) is True
    assert len(sender.sent_commands) == 1
    assert sender.sent_commands[0].symbol == "USDJPY"
    assert sender.sent_commands[0].type == "BUY"


def test_mock_order_sender_clear() -> None:
    """clear() で送信履歴が空になる"""
    sender = MockOrderSender()
    sender.send_order(OrderCommand(action="ORDER", symbol="USDJPY", type="BUY", lots=0.01))
    sender.clear()
    assert len(sender.sent_commands) == 0
