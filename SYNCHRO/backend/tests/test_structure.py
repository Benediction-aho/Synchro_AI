import pytest

from synchro.services.agent_engine.intelligence.structure import (
    BreakOfStructure,
    Direction,
    StructureError,
    find_break_of_structure,
    find_fair_value_gaps,
    find_order_blocks,
)


def _candle(epoch, o, h, l, c):
    return {"epoch": epoch, "open": o, "high": h, "low": l, "close": c}


def _uptrend_then_ob():
    candles = [_candle(i, 100 + i, 101 + i, 99.5 + i, 100.5 + i) for i in range(10)]
    candles.append(_candle(10, 110, 110.5, 105, 106))
    for i in range(11, 20):
        candles.append(_candle(i, 106 + (i - 11), 108 + (i - 11), 105.5 + (i - 11), 107.5 + (i - 11)))
    return candles


class TestValidation:
    def test_rejects_non_list(self):
        with pytest.raises(StructureError):
            find_order_blocks("not-a-list")

    def test_rejects_too_short(self):
        with pytest.raises(StructureError):
            find_fair_value_gaps([_candle(0, 1, 1, 1, 1)])

    def test_rejects_malformed_keys(self):
        good = _candle(0, 1, 2, 0.5, 1.5)
        bad = {"open": 1, "high": 2}
        candles = [good, bad, good, good, good]
        with pytest.raises(StructureError, match="malformed candle"):
            find_order_blocks(candles)

    def test_rejects_nan_prices(self):
        good = _candle(0, 1, 2, 0.5, 1.5)
        bad = _candle(1, float("nan"), 2, 1, 1.5)
        candles = [good, bad, good, good, good]
        with pytest.raises(StructureError, match="non-finite"):
            find_order_blocks(candles)

    def test_rejects_ohlc_invariant_violation(self):
        good = _candle(0, 1, 2, 0.5, 1.5)
        bad = _candle(1, 1, 2, 3, 4)
        candles = [good, bad, good, good, good]
        with pytest.raises(StructureError, match="invariant"):
            find_order_blocks(candles)

    def test_rejects_oversized_input(self):
        from synchro.services.agent_engine.intelligence.structure import MAX_CANDLES

        huge = [_candle(i, 1, 2, 0.5, 1.5) for i in range(MAX_CANDLES + 1)]
        with pytest.raises(StructureError, match="safety bound"):
            find_order_blocks(huge)

    def test_rejects_bad_parameters(self):
        candles = _uptrend_then_ob()
        with pytest.raises(StructureError):
            find_order_blocks(candles, lookback=0)
        with pytest.raises(StructureError):
            find_break_of_structure(candles, swing_window=0)


class TestOrderBlocks:
    def test_detects_bullish_ob_before_displacement_up(self):
        blocks = find_order_blocks(_uptrend_then_ob(), lookback=3)
        bullish = [b for b in blocks if b.direction == Direction.BULLISH]
        assert bullish, "expected at least one bullish order block"
        ob = bullish[-1]
        assert ob.index >= 10
        assert not ob.mitigated

    def test_marks_mitigated_when_price_returns_through_block(self):
        candles = _uptrend_then_ob()
        early_blocks = find_order_blocks(candles, lookback=3)
        early_bullish = [b for b in early_blocks if b.direction == Direction.BULLISH]
        assert early_bullish

        candles.append(_candle(25, 95, 96, 90, 91))
        after = find_order_blocks(candles, lookback=3)
        for b in after:
            if b.direction == Direction.BULLISH and b.index == early_bullish[-1].index:
                assert b.mitigated

    def test_respects_max_blocks(self):
        candles = []
        price = 100.0
        epoch = 0
        for cycle in range(30):
            candles.append(_candle(epoch, price, price + 1, price - 1, price - 0.5))
            epoch += 1
            for k in range(4):
                price += 1
                candles.append(_candle(epoch, price - 1, price + 1, price - 2, price))
                epoch += 1
            price -= 6
        blocks = find_order_blocks(candles, lookback=3, max_blocks=5)
        assert len(blocks) <= 5


class TestFairValueGaps:
    def test_detects_bullish_fvg(self):
        candles = [
            _candle(0, 100, 101, 99, 100.5),
            _candle(1, 103, 106, 102.5, 105.5),
            _candle(2, 105, 107, 104, 106),
        ]
        gaps = find_fair_value_gaps(candles)
        bull = [g for g in gaps if g.direction == Direction.BULLISH]
        assert len(bull) == 1
        assert bull[0].bottom == 101 and bull[0].top == 104
        assert not bull[0].filled

    def test_detects_bearish_fvg_and_fill(self):
        candles = [
            _candle(0, 110, 111, 109, 109.5),
            _candle(1, 106, 106.5, 103, 103.5),
            _candle(2, 104, 105, 102, 102.5),
        ]
        gaps = find_fair_value_gaps(candles)
        bear = [g for g in gaps if g.direction == Direction.BEARISH]
        assert len(bear) == 1

        fill = _candle(5, 108, 112, 107.5, 111)
        gaps2 = find_fair_value_gaps(candles + [fill])
        bear2 = [g for g in gaps2 if g.direction == Direction.BEARISH]
        assert bear2[0].filled

    def test_no_gap_when_wicks_overlap(self):
        candles = [
            _candle(0, 100, 105, 95, 100),
            _candle(1, 100, 105, 95, 100),
            _candle(2, 100, 105, 95, 100),
        ]
        assert find_fair_value_gaps(candles) == []


class TestBreakOfStructure:
    def test_detects_bullish_bos_on_plateau_breakout(self):
        candles = []
        for i in range(11):
            high = 105.0 if i == 4 else 101.0
            candles.append(_candle(i, 100, high, 99, 100))
        candles.append(_candle(11, 100, 106.5, 99.5, 106))

        bos = find_break_of_structure(candles, swing_window=3)
        bull = [b for b in bos if b.direction == Direction.BULLISH]
        assert bull, "expected a bullish BOS on the breakout"
        assert bull[0].index == 11
        assert bull[0].level == 105.0

    def test_alternation_prevents_same_direction_spam(self):
        points = [100, 112, 90, 124, 82, 136, 74]
        per_leg = 7
        candles = []
        epoch = 0
        for a, b in zip(points, points[1:]):
            step = (b - a) / per_leg
            for j in range(per_leg):
                o = a + step * j
                c = a + step * (j + 1)
                candles.append(
                    _candle(epoch, o, max(o, c) + 0.5, min(o, c) - 0.5, c)
                )
                epoch += 1

        bos = find_break_of_structure(candles, swing_window=3)
        directions = [b.direction for b in bos]
        assert len(directions) >= 2
        for a, b in zip(directions, directions[1:]):
            assert a != b, "consecutive BOS must alternate direction"
