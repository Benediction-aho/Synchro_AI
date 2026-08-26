import pytest

from synchro.services.agent_engine.intelligence.candles import CandleError
from synchro.services.agent_engine.intelligence.momentum import (
    bollinger_position,
    macd,
    momentum_confluence,
    rsi,
    stochastic,
)
from synchro.services.agent_engine.intelligence.trend import (
    evaluate_timeframe,
    multi_tf_alignment,
    validate_trend_block,
)


def _trend_candles(start, end, count=120):
    candles = []
    price = start
    step = (end - start) / count
    for i in range(count):
        o = price
        c = price + step
        candles.append(
            {"epoch": i, "open": o, "high": max(o, c) + 0.4, "low": min(o, c) - 0.4, "close": c}
        )
        price = c
    return candles


UP = _trend_candles(100, 160)
DOWN = _trend_candles(160, 100)


class TestTimeframeValidator:
    def test_uptrend_timeframe_is_bullish(self):
        vote = evaluate_timeframe(UP, "M15")
        assert vote.trend == "bullish"

    def test_downtrend_timeframe_is_bearish(self):
        vote = evaluate_timeframe(DOWN, "H1")
        assert vote.trend == "bearish"

    def test_multi_tf_alignment_all_bullish(self):
        alignment, votes = validate_trend_block({"M15": UP, "H1": UP, "H4": UP})
        assert alignment == "bullish"
        assert len(votes) == 3

    def test_multi_tf_mixed_is_none(self):
        alignment, _ = validate_trend_block({"M15": UP, "H1": DOWN})
        assert alignment is None

    def test_fast_period_must_be_smaller(self):
        with pytest.raises(CandleError):
            evaluate_timeframe(UP, "M15", fast_period=50, slow_period=20)

    def test_rejects_short_series(self):
        with pytest.raises(CandleError):
            evaluate_timeframe(_trend_candles(100, 102, count=30), "M15")

    def test_empty_tf_dict_rejected(self):
        with pytest.raises(CandleError):
            validate_trend_block({})


class TestOscillators:
    def test_rsi_bounds_and_overbought(self):
        value = rsi(__import__("numpy").array([float(i) for i in range(1, 40)]))
        assert 0 <= value <= 100
        assert value == 100.0

    def test_rsi_pure_decline_is_zero(self):
        import numpy as np

        value = rsi(np.array([float(-i) for i in range(1, 40)]))
        assert value < 20

    def test_stochastic_range(self):
        k, d = stochastic(UP_H := [c["high"] for c in UP], [c["low"] for c in UP], [c["close"] for c in UP])
        assert 0 <= k <= 100 and 0 <= d <= 100

    def test_macd_positive_in_uptrend(self):
        line, signal = macd(__import__("numpy").array([c["close"] for c in UP]))
        assert line > signal

    def test_macd_rejects_fast_ge_slow(self):
        with pytest.raises(CandleError):
            macd(__import__("numpy").array([c["close"] for c in UP]), fast=26, slow=12)

    def test_bollinger_position_clamped(self):
        pos = bollinger_position(__import__("numpy").array([c["close"] for c in UP]))
        assert -1.0 <= pos <= 1.0

    def test_bounded_periods_reject_abuse(self):
        with pytest.raises(CandleError):
            rsi(__import__("numpy").array([c["close"] for c in UP]), period=0)
        with pytest.raises(CandleError):
            stochastic(
                [c["high"] for c in UP],
                [c["low"] for c in UP],
                [c["close"] for c in UP],
                k_period=10_000,
            )
        with pytest.raises(CandleError):
            bollinger_position(__import__("numpy").array([c["close"] for c in UP]), num_std=99)


class TestConfluence:
    def test_uptrend_scores_positive(self):
        snapshot = momentum_confluence(UP)
        assert snapshot.score > 0.2

    def test_downtrend_scores_negative(self):
        snapshot = momentum_confluence(DOWN)
        assert snapshot.score < -0.2

    def test_score_clamped_to_unit_range(self):
        snapshot = momentum_confluence(UP)
        assert -1.0 <= snapshot.score <= 1.0

    def test_votes_consistent_with_components(self):
        snapshot = momentum_confluence(DOWN)
        if snapshot.macd_line < snapshot.macd_signal:
            assert snapshot.votes["macd"] == -1

    def test_rejects_insufficient_data(self):
        with pytest.raises(CandleError):
            momentum_confluence(_trend_candles(100, 101, count=20))
