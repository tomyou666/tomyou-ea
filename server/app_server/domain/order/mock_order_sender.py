"""テスト用モック命令部"""

from app_server.domain.order.base import OrderSender
from app_server.models.trading import OrderCommand, OrderInfoList, PriceInfo


class MockOrderSender(OrderSender):
    """送信内容をメモリに保持し、検証用に公開するテスト用命令部"""

    def __init__(self) -> None:
        self.send_commands: list[OrderCommand] = []
        self.send_payloads: list[dict] = []  # _send_payload で送ったペイロード（order 層内部用）
        self.send_result: bool = True  # テストで成功/失敗を切り替え可能

    def _send_payload(self, payload: dict) -> bool:
        """送信ペイロードを記録する。"""
        self.send_payloads.append(payload)
        return self.send_result

    def send_order(self, order_command: OrderCommand) -> bool:
        self.send_commands.append(order_command)
        payload = order_command.model_dump(mode="json", exclude_none=True)
        self.send_payloads.append(payload)
        return self.send_result

    async def get_price_info(self, symbol: str) -> PriceInfo:
        """モック: 固定の PriceInfo を返す。"""
        return PriceInfo(
            type="price_info",
            request_id="mock-price",
            symbol=symbol,
            point=0.001,
            digits=3,
            pips=0.01,
        )

    async def get_order_info(self, ticket: int | None = None) -> OrderInfoList:
        """モック: 空の OrderInfoList を返す。"""
        return OrderInfoList(
            type="order_info_list",
            request_id="mock-order",
            count=0,
            orders=[],
        )

    def clear(self) -> None:
        """送信履歴をクリアする。"""
        self.send_commands.clear()
        self.send_payloads.clear()
