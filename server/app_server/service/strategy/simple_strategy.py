"""シンプルな戦略の例"""

from app_server.model.trading import Signal, SignalResult, TickDto
from app_server.service.strategy.base import Strategy


class SimpleStrategy(Strategy):
    """シンプル戦略: スプレッド制限＋前ティックとのミッド価格差で買い/売り/ホールドを判定。

    - スプレッドが閾値より大きい → HOLD
    - ミッド価格が前ティックより閾値以上上昇 → BUY
    - ミッド価格が前ティックより閾値以上下落 → SELL
    - それ以外 → HOLD
    """

    def __init__(
        self,
        max_spread: int = 5,
        default_lots: float = 0.01,
        momentum_pips: float = 0.0001,
        sl_pips: float = 0.0,
        tp_pips: float = 0.0,
    ) -> None:
        self.max_spread = max_spread
        self.default_lots = default_lots
        self.momentum_pips = momentum_pips
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self._prev_mid: float | None = None

    def next(self, tick: TickDto, context: object | None = None) -> Signal | SignalResult:
        if tick.spread > self.max_spread:
            return SignalResult(
                signal=Signal.HOLD,
                lots=self.default_lots,
                sl=self.sl_pips,
                tp=self.tp_pips,
            )
        mid = (tick.bid + tick.ask) / 2.0
        signal = Signal.HOLD
        if self._prev_mid is not None:
            diff = mid - self._prev_mid
            if diff >= self.momentum_pips:
                signal = Signal.BUY
            elif diff <= -self.momentum_pips:
                signal = Signal.SELL
        self._prev_mid = mid
        return SignalResult(
            signal=signal,
            lots=self.default_lots,
            sl=self.sl_pips,
            tp=self.tp_pips,
        )
