import pytest

from synchro.services.agent_engine.intelligence.score_engine import (
    Decision,
    Guardrails,
    MarketContext,
    decide,
    detect_trigger,
    evaluate_score,
    run_filters,
)
from synchro.services.agent_engine.intelligence.structure import (
    BreakOfStructure,
    Direction,
    OrderBlock,
)


def _candle(i, o, h, l, c):
    return {"epoch": i, "open": o, "high": h, "low": l, "close": c}


def _bull_series():
    candles = []
    price = 100.0
    for i in range(30):
        o = price
        c = price + 0.6
        candles.append(_candle(i, o, c + 0.3, o - 0.4, c))
        price = c
    candles.append(_candle(30, 117.0, 118.2, 116.5, 118.0))
    candles.append(_candle(31, 116.0, 116.5, 112.4, 113.0))
    candles.append(_candle(32, 113.0, 113.1, 109.9, 112.4))
    return candles


def _context(**overrides) -> MarketContext:
    base = dict(
        symbol="R_75",
        direction_hint="BUY",
        regime="trend_up",
        trend_alignment="bullish",
        momentum_score=0.6,
        rsi=58.0,
        candles=_bull_series(),
        order_blocks=[OrderBlock(Direction.BULLISH, 20, 112.0, 110.0, False)],
        fair_value_gaps=[],
        bos_events=[BreakOfStructure(Direction.BULLISH, 28, 111.5)],
    )
    base.update(overrides)
    return MarketContext(**base)


class TestTriggers:
    def test_bullish_engulfing_detected(self):
        candles = [_candle(0, 105, 105.8, 103.9, 104.1), _candle(1, 103.8, 106.4, 103.7, 106.2)]
        assert detect_trigger(candles) == "bullish_engulfing"

    def test_bearish_engulfing_detected(self):
        candles = [_candle(0, 104, 105.9, 103.9, 105.8), _candle(1, 106.1, 106.3, 103.6, 103.8)]
        assert detect_trigger(candles) == "bearish_engulfing"

    def test_bullish_pin_detected(self):
        candles = [
            _candle(0, 100, 101, 99, 100.5),
            _candle(1, 100.5, 100.8, 98.0, 100.6),
        ]
        assert detect_trigger(candles) == "bullish_pin"

    def test_no_trigger_on_flat_candles(self):
        candles = [_candle(0, 100, 100.1, 99.9, 100.0), _candle(1, 100, 100.1, 99.95, 100.05)]
        assert detect_trigger(candles) is None

    def test_rejects_single_candle(self):
        assert detect_trigger([_candle(0, 1, 2, 0.5, 1.5)]) is None


class TestFilters:
    def test_clean_context_passes_all_15(self):
        failed = run_filters(_context(), Guardrails())
        assert failed == []

    def test_each_violation_reported_by_name(self):
        cases = {
            "spread_within_limit": Guardrails(spread_pips=5.0),
            "session_allowed": Guardrails(session_allowed=False),
            "market_open": Guardrails(market_open=False),
            "no_news_blackout": Guardrails(news_blackout=True),
            "atr_above_floor": Guardrails(atr=0.01, atr_min=0.5),
            "atr_below_ceiling": Guardrails(atr=999.0, atr_max=10.0),
            "regime_not_crisis": None,
            "no_recent_opposite_bos": Guardrails(recent_opposite_bos=True),
            "balance_ok": Guardrails(balance_ok=False),
            "daily_loss_ok": Guardrails(daily_loss_ok=False),
            "open_trades_under_cap": Guardrails(open_trades=5, max_open_trades=2),
            "cooldown_ok": Guardrails(cooldown_ok=False),
        }
        for expected_failure, guard in cases.items():
            if guard is None:
                ctx = _context(regime="crisis")
                guards = Guardrails()
            else:
                ctx = _context()
                guards = guard
            failed = run_filters(ctx, guards)
            assert expected_failure in failed, f"{expected_failure} should fail"

    def test_trend_mismatch_and_rsi_extreme(self):
        assert "trend_supports_direction" in run_filters(
            _context(trend_alignment=None), Guardrails()
        )
        assert "trend_supports_direction" in run_filters(
            _context(direction_hint="SELL", trend_alignment="bullish"), Guardrails()
        )
        assert "rsi_not_extreme" in run_filters(_context(rsi=80.0), Guardrails())
        assert "rsi_not_extreme" in run_filters(_context(rsi=20.0), Guardrails())

    def test_zone_filter_fails_without_structure(self):
        bare = _context(order_blocks=[], bos_events=[])
        assert "entry_near_unmitigated_zone" in run_filters(bare, Guardrails())


class TestScore:
    def test_perfect_setup_scores_five_five(self):
        components = evaluate_score(_context())
        assert all(components.values())
        decision = decide(_context(), Guardrails())
        assert decision.decision == "BUY"
        assert decision.score == 5

    def test_four_of_five_waits_with_missing_names(self):
        context = _context(momentum_score=-0.6)
        decision = decide(context, Guardrails())
        assert decision.decision == "WAIT"
        assert decision.score == 4
        assert "momentum" in decision.reason_text

    def test_regime_gate_blocks_sell_in_uptrend(self):
        components = evaluate_score(_context(direction_hint="SELL"))
        assert components["regime"] is False
        assert components["trend"] is False

    def test_filter_block_short_circuits_score(self):
        decision = decide(_context(), Guardrails(news_blackout=True))
        assert decision.decision == "WAIT"
        assert decision.components == {}
        assert decision.failed_filters == ["no_news_blackout"]


class TestTransparency:
    def test_snapshot_serializable_for_signals_table(self):
        import json

        decision = decide(_context(momentum_score=-0.6), Guardrails(news_blackout=True))
        payload = json.dumps(decision.to_snapshot())
        assert "no_news_blackout" in payload
        assert isinstance(json.loads(payload), dict)

    def test_reason_text_nonempty_always(self):
        for decision in (
            decide(_context(), Guardrails()),
            decide(_context(), Guardrails(cooldown_ok=False)),
            decide(_context(momentum_score=-0.9), Guardrails()),
        ):
            assert decision.reason_text

    def test_invalid_direction_hint_rejected(self):
        with pytest.raises(ValueError):
            evaluate_score(_context(direction_hint="MAYBE"))
