"""テスト用モック命令部（設計書 4.5, 10.4）"""

from app_server.model.trading import OrderCommand
from app_server.service.order.base import OrderSender


class MockOrderSender(OrderSender):
    """送信内容をメモリに保持し、検証用に公開するテスト用命令部"""

    def __init__(self) -> None:
        self.sent_commands: list[OrderCommand] = []
        self.send_result: bool = True  # テストで成功/失敗を切り替え可能

    def send_order(self, order_command: OrderCommand) -> bool:
        self.sent_commands.append(order_command)
        return self.send_result

    def clear(self) -> None:
        """送信履歴をクリアする。"""
        self.sent_commands.clear()
