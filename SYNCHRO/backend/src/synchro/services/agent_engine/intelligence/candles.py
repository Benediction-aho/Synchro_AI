"""Shared OHLCV validation for all intelligence modules.

Every module that consumes market data goes through here so malformed,
unbounded or hostile inputs are rejected at the boundary.
"""

from typing import Any

import numpy as np

_REQUIRED_KEYS = ("epoch", "open", "high", "low", "close")
MAX_CANDLES = 100_000


class CandleError(ValueError):
    pass


def to_candle_array(
    candles: list[dict[str, Any]], min_length: int, max_length: int = MAX_CANDLES
) -> np.ndarray:
    if not isinstance(candles, list):
        raise CandleError("candles must be a list")
    if len(candles) < min_length:
        raise CandleError(f"need at least {min_length} candles, got {len(candles)}")
    if len(candles) > max_length:
        raise CandleError(f"candle count exceeds safety bound ({max_length})")
    rows = []
    for i, c in enumerate(candles):
        try:
            values = [float(c[k]) for k in _REQUIRED_KEYS]
        except (KeyError, TypeError, ValueError) as exc:
            raise CandleError(f"malformed candle at index {i}") from exc
        epoch, o, h, l, cl = values
        if not all(np.isfinite(v) for v in (o, h, l, cl)):
            raise CandleError(f"non-finite price in candle at index {i}")
        if h < max(o, cl) - 1e-12 or l > min(o, cl) + 1e-12 or h < l:
            raise CandleError(f"OHLC invariant violated at index {i}")
        rows.append((epoch, o, h, l, cl))
    return np.array(rows, dtype=float)


def bounded_period(period: int, low: int = 2, high: int = 500) -> int:
    if not isinstance(period, int) or not (low <= period <= high):
        raise CandleError(f"period must be an integer in [{low}, {high}], got {period!r}")
    return period


def ema(values: np.ndarray, period: int) -> np.ndarray:
    bounded_period(period)
    if values.size < period:
        raise CandleError(f"ema needs >= {period} values, got {values.size}")
    alpha = 2.0 / (period + 1.0)
    out = np.empty_like(values)
    out[0] = values[0]
    for i in range(1, values.size):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]
    return out
