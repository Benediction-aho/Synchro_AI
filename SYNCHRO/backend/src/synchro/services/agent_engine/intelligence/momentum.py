"""APEX Layer 6 (MOMENTUM): oscillator confluence engine.

RSI, Stochastic, MACD and Bollinger position each cast a vote in {-1, 0, +1}.
The confluence score is the weighted sum, clamped to [-1, +1].
"""

from dataclasses import dataclass

import numpy as np

from synchro.services.agent_engine.intelligence.candles import (
    CandleError,
    bounded_period,
    ema,
    to_candle_array,
)

_WEIGHTS = {"rsi": 0.25, "stoch": 0.20, "macd": 0.30, "bollinger": 0.25}


@dataclass(frozen=True)
class MomentumSnapshot:
    rsi: float
    stoch_k: float
    stoch_d: float
    macd_line: float
    macd_signal: float
    bollinger_position: float
    score: float
    votes: dict


def _vote(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def rsi(closes: np.ndarray, period: int = 14) -> float:
    bounded_period(period)
    if closes.size < period + 1:
        raise CandleError(f"rsi needs >= {period + 1} closes")
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[-period:]))
    avg_loss = float(np.mean(losses[-period:]))
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def stochastic(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, k_period: int = 14, d_period: int = 3
) -> tuple[float, float]:
    bounded_period(k_period)
    bounded_period(d_period)
    highs, lows, closes = (np.asarray(x, dtype=float) for x in (highs, lows, closes))
    n = closes.size
    if n < k_period + d_period:
        raise CandleError(f"stochastic needs >= {k_period + d_period} candles")
    k_values = []
    for t in range(k_period - 1, n):
        hh = float(highs[t - k_period + 1 : t + 1].max())
        ll = float(lows[t - k_period + 1 : t + 1].min())
        rng = hh - ll
        k_values.append(100.0 * (float(closes[t]) - ll) / rng if rng > 0 else 50.0)
    k_arr = np.array(k_values)
    d_value = float(np.mean(k_arr[-d_period:]))
    return float(k_arr[-1]), d_value


def macd(
    closes: np.ndarray, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> tuple[float, float]:
    bounded_period(fast)
    bounded_period(slow)
    bounded_period(signal_period)
    if fast >= slow or closes.size < slow + signal_period:
        raise CandleError(f"macd needs >= {slow + signal_period} closes and fast<slow")
    macd_line = ema(closes, fast) - ema(closes, slow)
    signal_line = ema(macd_line, signal_period)
    return float(macd_line[-1]), float(signal_line[-1])


def bollinger_position(closes: np.ndarray, period: int = 20, num_std: float = 2.0) -> float:
    bounded_period(period)
    if not (0.5 <= num_std <= 5.0):
        raise CandleError("num_std must be in [0.5, 5.0]")
    if closes.size < period:
        raise CandleError(f"bollinger needs >= {period} closes")
    window = closes[-period:]
    mid = float(np.mean(window))
    std = float(np.std(window))
    upper = mid + num_std * std
    lower = mid - num_std * std
    band = upper - lower
    if band <= 0:
        return 0.0
    return max(-1.0, min(1.0, (float(closes[-1]) - mid) / (band / 2.0)))


def momentum_confluence(candles: list[dict]) -> MomentumSnapshot:
    arr = to_candle_array(candles, min_length=40)
    highs, lows, closes = arr[:, 2], arr[:, 3], arr[:, 4]

    r = rsi(closes, 14)
    rsi_vote = 0
    if 55 < r < 70:
        rsi_vote = 1
    elif 30 < r < 45:
        rsi_vote = -1

    k, d = stochastic(highs, lows, closes, 14, 3)
    stoch_vote = 0
    if k > d and k < 80:
        stoch_vote = 1
    elif k < d and k > 20:
        stoch_vote = -1

    m, s = macd(closes, 12, 26, 9)
    macd_vote = _vote(m - s)

    bp = bollinger_position(closes, 20, 2.0)
    bb_vote = 1 if bp > 0.25 else (-1 if bp < -0.25 else 0)

    votes = {"rsi": rsi_vote, "stoch": stoch_vote, "macd": macd_vote, "bollinger": bb_vote}
    score = sum(_WEIGHTS[name] * v for name, v in votes.items())
    score = max(-1.0, min(1.0, score))

    return MomentumSnapshot(
        rsi=r,
        stoch_k=k,
        stoch_d=d,
        macd_line=m,
        macd_signal=s,
        bollinger_position=bp,
        score=round(score, 4),
        votes=votes,
    )
