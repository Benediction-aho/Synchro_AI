"""APEX Layer 5 (TREND): multi-timeframe EMA alignment validator.

Each timeframe votes bullish/bearish/neutral based on close vs EMA(fast) vs
EMA(slow). A trade direction is only supported when every configured
timeframe agrees.
"""

from dataclasses import dataclass

import numpy as np

from synchro.services.agent_engine.intelligence.candles import (
    CandleError,
    bounded_period,
    ema,
    to_candle_array,
)


@dataclass(frozen=True)
class TimeframeVote:
    timeframe: str
    trend: str
    close: float
    ema_fast: float
    ema_slow: float


def evaluate_timeframe(
    candles: list[dict], timeframe: str, fast_period: int = 20, slow_period: int = 50
) -> TimeframeVote:
    if not timeframe or len(timeframe) > 16:
        raise CandleError("invalid timeframe label")
    bounded_period(fast_period)
    bounded_period(slow_period)
    if fast_period >= slow_period:
        raise CandleError("fast EMA period must be smaller than slow EMA period")

    arr = to_candle_array(candles, min_length=slow_period + period_buffer(slow_period))
    closes = arr[:, 4]
    fast_line = ema(closes, fast_period)
    slow_line = ema(closes, slow_period)
    close = float(closes[-1])
    f, s = float(fast_line[-1]), float(slow_line[-1])

    if close > f > s:
        trend = "bullish"
    elif close < f < s:
        trend = "bearish"
    else:
        trend = "neutral"

    return TimeframeVote(timeframe, trend, close, f, s)


def period_buffer(slow_period: int) -> int:
    return min(slow_period, 100)


def multi_tf_alignment(votes: list[TimeframeVote]) -> str | None:
    """Return the aligned direction only when every timeframe agrees."""
    if not votes:
        raise CandleError("need at least one timeframe vote")
    trends = {v.trend for v in votes}
    if len(trends) == 1 and trends != {"neutral"}:
        return next(iter(trends))
    return None


def validate_trend_block(
    candles_by_tf: dict[str, list[dict]],
    fast_period: int = 20,
    slow_period: int = 50,
) -> tuple[str | None, list[TimeframeVote]]:
    if not candles_by_tf:
        raise CandleError("no timeframes provided")
    votes = [
        evaluate_timeframe(candles, tf, fast_period, slow_period)
        for tf, candles in sorted(candles_by_tf.items())
    ]
    return multi_tf_alignment(votes), votes


__all__ = [
    "TimeframeVote",
    "evaluate_timeframe",
    "multi_tf_alignment",
    "validate_trend_block",
    "np",
]
