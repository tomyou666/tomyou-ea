"""命令部モックテスト"""

import pytest
from app_server.domain.sender.mock_order_sender import MockOrderSender
from app_server.models.trading import OrderCommand


def test_mock_order_sender_records_commands() -> None:
    """送信した OrderCommand が send_commands に記録される"""
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
    assert len(sender.send_commands) == 1
    assert sender.send_commands[0].symbol == "USDJPY"
    assert sender.send_commands[0].type == "BUY"


def test_mock_order_sender_clear() -> None:
    """clear() で送信履歴が空になる"""
    sender = MockOrderSender()
    sender.send_order(OrderCommand(action="ORDER", symbol="USDJPY", type="BUY", lots=0.01))
    sender.clear()
    assert len(sender.send_commands) == 0
