"""移動平均クロスオーバー戦略（設計書 4.3）

短期MAが長期MAを上抜け → 買い、下抜け → 売り。それ以外はホールド。
"""

from collections import deque

from app_server.model.trading import Signal, SignalResult, TickDto
from app_server.service.strategy.base import Strategy


class MACrossoverStrategy(Strategy):
    """移動平均クロスオーバー戦略。

    - ミッド価格 (bid+ask)/2 の短期・長期移動平均を計算
    - ゴールデンクロス（短期 > 長期）→ BUY
    - デッドクロス（短期 < 長期）→ SELL
    - スプレッドが閾値より大きい場合は HOLD
    """

    def __init__(
        self,
        short_period: int = 5,
        long_period: int = 15,
        max_spread: int = 10,
        default_lots: float = 0.01,
        sl_pips: float = 0.0,
        tp_pips: float = 0.0,
    ) -> None:
        if short_period >= long_period:
            raise ValueError("short_period は long_period より小さくしてください")
        self.short_period = short_period
        self.long_period = long_period
        self.max_spread = max_spread
        self.default_lots = default_lots
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        # 直近のミッド価格を保持（long_period 分あれば長期MAが計算できる）
        self._mid_prices: deque[float] = deque(maxlen=long_period + 5)
        self._prev_short_ma: float | None = None
        self._prev_long_ma: float | None = None

    def _mid(self, tick: TickDto) -> float:
        return (tick.bid + tick.ask) / 2.0

    def _short_ma(self) -> float | None:
        if len(self._mid_prices) < self.short_period:
            return None
        return sum(list(self._mid_prices)[-self.short_period :]) / self.short_period

    def _long_ma(self) -> float | None:
        if len(self._mid_prices) < self.long_period:
            return None
        return sum(list(self._mid_prices)[-self.long_period :]) / self.long_period

    def next(
        self, tick: TickDto, context: object | None = None
    ) -> Signal | SignalResult:
        if tick.spread > self.max_spread:
            return SignalResult(
                signal=Signal.HOLD,
                lots=self.default_lots,
                sl=self.sl_pips,
                tp=self.tp_pips,
            )

        mid = self._mid(tick)
        self._mid_prices.append(mid)

        short_ma = self._short_ma()
        long_ma = self._long_ma()
        if short_ma is None or long_ma is None:
            self._prev_short_ma = short_ma
            self._prev_long_ma = long_ma
            return SignalResult(
                signal=Signal.HOLD,
                lots=self.default_lots,
                sl=self.sl_pips,
                tp=self.tp_pips,
            )

        # クロスオーバー判定（前回のMAが必要）
        signal = Signal.HOLD
        if self._prev_short_ma is not None and self._prev_long_ma is not None:
            # ゴールデンクロス: 短期が長期を下から上へ
            if self._prev_short_ma <= self._prev_long_ma and short_ma > long_ma:
                signal = Signal.BUY
            # デッドクロス: 短期が長期を上から下へ
            elif self._prev_short_ma >= self._prev_long_ma and short_ma < long_ma:
                signal = Signal.SELL

        self._prev_short_ma = short_ma
        self._prev_long_ma = long_ma

        return SignalResult(
            signal=signal,
            lots=self.default_lots,
            sl=self.sl_pips,
            tp=self.tp_pips,
        )
