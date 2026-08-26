"""M3 execution logic: 15 hard filters + the non-negotiable 5/5 score.

Decision flow (Commandment IX - every refusal is explainable):
  1. run all 15 filters -> any failure means WAIT with named reasons
  2. evaluate the 5 score components -> trade only on exactly 5/5
Output is fully serializable for signals.reason_text / trades.filters_snapshot.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from synchro.services.agent_engine.intelligence.structure import (
    BreakOfStructure,
    Direction,
    FairValueGap,
    OrderBlock,
)


@dataclass
class MarketContext:
    symbol: str
    direction_hint: str
    regime: str
    trend_alignment: str | None
    momentum_score: float
    rsi: float
    candles: list[dict]
    order_blocks: list[OrderBlock] = field(default_factory=list)
    fair_value_gaps: list[FairValueGap] = field(default_factory=list)
    bos_events: list[BreakOfStructure] = field(default_factory=list)


@dataclass
class Guardrails:
    spread_pips: float = 0.5
    max_spread_pips: float = 1.5
    session_allowed: bool = True
    market_open: bool = True
    news_blackout: bool = False
    atr: float = 1.0
    atr_min: float = 0.0
    atr_max: float = float("inf")
    recent_opposite_bos: bool = False
    balance_ok: bool = True
    daily_loss_ok: bool = True
    open_trades: int = 0
    max_open_trades: int = 2
    cooldown_ok: bool = True


@dataclass
class Decision:
    decision: str
    score: int
    components: dict[str, bool]
    failed_filters: list[str]
    reason_text: str

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "score": self.score,
            "components": self.components,
            "failed_filters": self.failed_filters,
        }


def _direction_of(hint: str) -> Direction | None:
    if hint == "BUY":
        return Direction.BULLISH
    if hint == "SELL":
        return Direction.BEARISH
    return None


def _near_zone(
    price: float,
    zones: list[tuple[float, float, Direction]],
    direction: Direction,
    tolerance: float,
) -> bool:
    top, bottom, zdir = None, None, None
    for z_top, z_bottom, z_dir in zones:
        if z_dir == direction and z_bottom - tolerance <= price <= z_top + tolerance:
            return True
    return False


def _zones_from(ctx: MarketContext) -> list[tuple[float, float, Direction]]:
    zones = [(ob.high, ob.low, ob.direction) for ob in ctx.order_blocks if not ob.mitigated]
    zones += [(g.top, g.bottom, g.direction) for g in ctx.fair_value_gaps if not g.filled]
    return zones


def _last_close_and_range(ctx: MarketContext) -> tuple[float, float]:
    arr_close = float(ctx.candles[-1]["close"])
    highs = np.array([c["high"] for c in ctx.candles[-14:]])
    lows = np.array([c["low"] for c in ctx.candles[-14:]])
    proxy_range = float((highs - lows).mean())
    return arr_close, proxy_range


def detect_trigger(candles: list[dict]) -> str | None:
    """Trigger-candle gate: engulfing or pin bar on the most recent closed candle."""
    if len(candles) < 2:
        return None
    c1, c2 = candles[-2], candles[-1]
    o1, cl1 = float(c1["open"]), float(c1["close"])
    o2, cl2 = float(c2["open"]), float(c2["close"])
    h2, l2 = float(c2["high"]), float(c2["low"])

    body1 = abs(cl1 - o1)
    body2 = abs(cl2 - o2)

    if cl1 < o1 and cl2 > o2 and cl2 > o1 and o2 < cl1 and body2 > body1:
        return "bullish_engulfing"
    if cl1 > o1 and cl2 < o2 and o2 > cl1 and cl2 < o1 and body2 > body1:
        return "bearish_engulfing"

    body = abs(cl2 - o2)
    upper_wick = h2 - max(o2, cl2)
    lower_wick = min(o2, cl2) - l2
    if body > 0 and lower_wick >= 2 * body and cl2 >= l2 + 0.66 * (h2 - l2):
        return "bullish_pin"
    if body > 0 and upper_wick >= 2 * body and cl2 <= l2 + 0.34 * (h2 - l2):
        return "bearish_pin"
    return None


_FILTERS: list[tuple[str, Any]] = [
    ("spread_within_limit", lambda m, g: g.spread_pips <= g.max_spread_pips),
    ("session_allowed", lambda m, g: g.session_allowed),
    ("market_open", lambda m, g: g.market_open),
    ("no_news_blackout", lambda m, g: not g.news_blackout),
    ("atr_above_floor", lambda m, g: g.atr >= g.atr_min),
    ("atr_below_ceiling", lambda m, g: g.atr <= g.atr_max),
    ("regime_not_crisis", lambda m, g: m.regime != "crisis"),
    ("no_recent_opposite_bos", lambda m, g: not g.recent_opposite_bos),
    ("balance_ok", lambda m, g: g.balance_ok),
    ("daily_loss_ok", lambda m, g: g.daily_loss_ok),
    ("open_trades_under_cap", lambda m, g: g.open_trades < g.max_open_trades),
    ("cooldown_ok", lambda m, g: g.cooldown_ok),
]


def _structural_filters():
    def entry_near_zone(m: MarketContext, g: Guardrails) -> bool:
        price, proxy_range = _last_close_and_range(m)
        tolerance = proxy_range * 0.75
        return _near_zone(price, _zones_from(m), _direction_of(m.direction_hint), tolerance)

    def trend_supports(m: MarketContext, g: Guardrails) -> bool:
        expected = {"BUY": "bullish", "SELL": "bearish"}.get(m.direction_hint)
        return m.trend_alignment == expected

    def rsi_not_extreme(m: MarketContext, g: Guardrails) -> bool:
        return 25.0 < m.rsi < 75.0

    return [
        ("entry_near_unmitigated_zone", entry_near_zone),
        ("trend_supports_direction", trend_supports),
        ("rsi_not_extreme", rsi_not_extreme),
    ]


_ALL_FILTERS = _FILTERS + _structural_filters()


def run_filters(market: MarketContext, guardrails: Guardrails) -> list[str]:
    failed = []
    for name, predicate in _ALL_FILTERS:
        try:
            passed = bool(predicate(market, guardrails))
        except Exception:
            passed = False
        if not passed:
            failed.append(name)
    return failed


def evaluate_score(market: MarketContext) -> dict[str, bool]:
    direction = _direction_of(market.direction_hint)
    if direction is None:
        raise ValueError("direction_hint must be BUY or SELL")

    regime_ok = {
        Direction.BULLISH: market.regime == "trend_up",
        Direction.BEARISH: market.regime == "trend_down",
    }[direction]

    trend_ok = market.trend_alignment == {"BUY": "bullish", "SELL": "bearish"}[market.direction_hint]

    wanted = 1 if market.direction_hint == "BUY" else -1
    momentum_ok = (
        np.sign(market.momentum_score) == wanted and abs(market.momentum_score) >= 0.2
    )

    price, proxy_range = _last_close_and_range(market)
    structure_ok = _near_zone(
        price, _zones_from(market), direction, proxy_range * 0.75
    ) or any(b.direction == direction for b in market.bos_events[-3:])

    trigger = detect_trigger(market.candles)
    trigger_ok = trigger is not None and (
        (direction == Direction.BULLISH and trigger.startswith("bullish"))
        or (direction == Direction.BEARISH and trigger.startswith("bearish"))
    )

    return {
        "regime": bool(regime_ok),
        "trend": bool(trend_ok),
        "momentum": bool(momentum_ok),
        "structure": bool(structure_ok),
        "trigger": bool(trigger_ok),
    }


def decide(market: MarketContext, guardrails: Guardrails) -> Decision:
    failed_filters = run_filters(market, guardrails)
    if failed_filters:
        return Decision(
            decision="WAIT",
            score=0,
            components={},
            failed_filters=failed_filters,
            reason_text=f"blocked by filters: {', '.join(failed_filters)}",
        )

    components = evaluate_score(market)
    score = sum(components.values())
    if score == 5:
        return Decision(
            decision=market.direction_hint,
            score=5,
            components=components,
            failed_filters=[],
            reason_text=f"5/5 confirmed for {market.direction_hint} on {market.symbol}",
        )
    missing = [name for name, ok in components.items() if not ok]
    return Decision(
        decision="WAIT",
        score=score,
        components=components,
        failed_filters=[],
        reason_text=f"score {score}/5 - missing: {', '.join(missing)}",
    )


__all__ = [
    "MarketContext",
    "Guardrails",
    "Decision",
    "detect_trigger",
    "run_filters",
    "evaluate_score",
    "decide",
]
