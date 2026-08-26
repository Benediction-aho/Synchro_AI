"""Market structure detection: Order Blocks, Fair Value Gaps, Break of Structure.

Pure functions over OHLCV candle dicts ({epoch, open, high, low, close}).
All inputs are validated and bounded; malformed candles are rejected loudly
rather than silently producing garbage signals (defense-in-depth: this module
feeds the execution path).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

_REQUIRED_KEYS = ("epoch", "open", "high", "low", "close")
MAX_CANDLES = 100_000


class StructureError(ValueError):
    pass


def _validate_candles(candles: list[dict[str, Any]], min_length: int) -> np.ndarray:
    if not isinstance(candles, list):
        raise StructureError("candles must be a list")
    if len(candles) < min_length:
        raise StructureError(f"need at least {min_length} candles, got {len(candles)}")
    if len(candles) > MAX_CANDLES:
        raise StructureError(f"candle count exceeds safety bound ({MAX_CANDLES})")
    rows = []
    for i, c in enumerate(candles):
        try:
            values = [float(c[k]) for k in _REQUIRED_KEYS]
        except (KeyError, TypeError, ValueError) as exc:
            raise StructureError(f"malformed candle at index {i}") from exc
        epoch, o, h, l, cl = values
        if not all(np.isfinite(v) for v in (o, h, l, cl)):
            raise StructureError(f"non-finite price in candle at index {i}")
        if h < max(o, cl) - 1e-12 or l > min(o, cl) + 1e-12 or h < l:
            raise StructureError(f"OHLC invariant violated at index {i}")
        rows.append((epoch, o, h, l, cl))
    return np.array(rows, dtype=float)


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True)
class OrderBlock:
    direction: Direction
    index: int
    high: float
    low: float
    mitigated: bool


@dataclass(frozen=True)
class FairValueGap:
    direction: Direction
    index: int
    top: float
    bottom: float
    filled: bool


@dataclass(frozen=True)
class BreakOfStructure:
    direction: Direction
    index: int
    level: float


def find_order_blocks(
    candles: list[dict[str, Any]], lookback: int = 3, max_blocks: int = 50
) -> list[OrderBlock]:
    """Order block = last opposite-color candle before a strong displacement leg.

    Bullish OB: down candle followed by `lookback` consecutive higher closes.
    Bearish OB: up candle followed by `lookback` consecutive lower closes.
    A block is 'mitigated' once any later candle trades back through its range.
    """
    if lookback < 1 or max_blocks < 1:
        raise StructureError("lookback and max_blocks must be >= 1")
    arr = _validate_candles(candles, min_length=lookback + 2)
    closes = arr[:, 4]
    blocks: list[OrderBlock] = []

    for i in range(len(arr) - lookback - 1):
        window = closes[i + 1 : i + 1 + lookback]
        body_up = arr[i, 4] < arr[i, 1]
        body_down = arr[i, 4] > arr[i, 1]

        if body_down and bool(np.all(np.diff(window) > 0)) and window[-1] > arr[i, 2]:
            blocks.append(
                OrderBlock(Direction.BULLISH, i, float(arr[i, 2]), float(arr[i, 3]), False)
            )
        elif body_up and bool(np.all(np.diff(window) < 0)) and window[-1] < arr[i, 3]:
            blocks.append(
                OrderBlock(Direction.BEARISH, i, float(arr[i, 2]), float(arr[i, 3]), False)
            )

    for j in range(len(blocks)):
        b = blocks[j]
        later_highs = arr[b.index + lookback + 1 :, 2]
        later_lows = arr[b.index + lookback + 1 :, 3]
        if b.direction == Direction.BULLISH and later_lows.size and float(later_lows.min()) <= b.low:
            blocks[j] = OrderBlock(b.direction, b.index, b.high, b.low, True)
        elif b.direction == Direction.BEARISH and later_highs.size and float(later_highs.max()) >= b.high:
            blocks[j] = OrderBlock(b.direction, b.index, b.high, b.low, True)

    return blocks[-max_blocks:]


def find_fair_value_gaps(
    candles: list[dict[str, Any]], max_gaps: int = 50
) -> list[FairValueGap]:
    """FVG = 3-candle imbalance where candle1 wick and candle3 wick don't overlap.

    Bullish FVG: low(candle3) > high(candle1). Gap zone = [high1, low3].
    Bearish FVG: high(candle3) < low(candle1). Gap zone = [high3, low1].
    A gap is 'filled' once any later candle trades through the whole zone.
    """
    if max_gaps < 1:
        raise StructureError("max_gaps must be >= 1")
    arr = _validate_candles(candles, min_length=3)
    gaps: list[FairValueGap] = []

    for i in range(len(arr) - 2):
        h1, l3 = arr[i, 2], arr[i + 2, 3]
        l1, h3 = arr[i, 3], arr[i + 2, 2]

        if l3 > h1:
            gaps.append(FairValueGap(Direction.BULLISH, i, float(l3), float(h1), False))
        elif h3 < l1:
            gaps.append(FairValueGap(Direction.BEARISH, i, float(h3), float(l1), False))

    for j, g in enumerate(gaps):
        later = arr[g.index + 2 :]
        if g.direction == Direction.BULLISH:
            filled = later.size and float(later[:, 3].min()) <= g.bottom
        else:
            filled = later.size and float(later[:, 2].max()) >= g.top
        if filled:
            gaps[j] = FairValueGap(g.direction, g.index, g.top, g.bottom, True)

    return gaps[-max_gaps:]


def find_break_of_structure(
    candles: list[dict[str, Any]], swing_window: int = 5
) -> list[BreakOfStructure]:
    """BOS = close beyond the most recent confirmed swing high/low.

    Swing highs/lows use a fractal definition: a bar whose high (low) is the
    extreme within `swing_window` bars on each side.
    """
    if swing_window < 1:
        raise StructureError("swing_window must be >= 1")
    arr = _validate_candles(candles, min_length=2 * swing_window + 2)
    highs, lows, closes = arr[:, 2], arr[:, 3], arr[:, 4]
    n = len(arr)

    swing_high_idx = [
        i
        for i in range(swing_window, n - swing_window)
        if highs[i] == highs[i - swing_window : i + swing_window + 1].max()
    ]
    swing_low_idx = [
        i
        for i in range(swing_window, n - swing_window)
        if lows[i] == lows[i - swing_window : i + swing_window + 1].min()
    ]

    breaks: list[BreakOfStructure] = []
    latest_high: int | None = None
    latest_low: int | None = None
    hi_ptr = 0
    lo_ptr = 0
    last_bos_dir: Direction | None = None

    for t in range(2 * swing_window + 1, n):
        while hi_ptr < len(swing_high_idx) and swing_high_idx[hi_ptr] + swing_window < t:
            latest_high = swing_high_idx[hi_ptr]
            hi_ptr += 1
        while lo_ptr < len(swing_low_idx) and swing_low_idx[lo_ptr] + swing_window < t:
            latest_low = swing_low_idx[lo_ptr]
            lo_ptr += 1

        broke_high = (
            latest_high is not None
            and closes[t] > highs[latest_high]
            and last_bos_dir != Direction.BULLISH
        )
        broke_low = (
            latest_low is not None
            and closes[t] < lows[latest_low]
            and last_bos_dir != Direction.BEARISH
        )

        if broke_high:
            breaks.append(
                BreakOfStructure(Direction.BULLISH, t, float(highs[latest_high]))
            )
            last_bos_dir = Direction.BULLISH
            latest_high = None
        elif broke_low:
            breaks.append(
                BreakOfStructure(Direction.BEARISH, t, float(lows[latest_low]))
            )
            last_bos_dir = Direction.BEARISH
            latest_low = None

    return breaks
