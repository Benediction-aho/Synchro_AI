import enum
from dataclasses import dataclass
from sqlalchemy.orm import Session

from synchro.core.timeutils import utcnow
from synchro.db.models.system import ActorType, AuditLog
from synchro.db.models.trading import Trade, TradeStatus
from synchro.db.models.learning import Pattern


class TradeEvent(str, enum.Enum):
    OPENED = "opened"
    PARTIAL_CLOSED = "partial_closed"
    BREAKEVEN_SET = "breakeven_set"
    TRAILING_ACTIVATED = "trailing_activated"
    CLOSED = "closed"


_EVENT_TARGET: dict[TradeEvent, TradeStatus | None] = {
    TradeEvent.OPENED: TradeStatus.OPEN,
    TradeEvent.PARTIAL_CLOSED: None,
    TradeEvent.BREAKEVEN_SET: TradeStatus.BREAKEVEN,
    TradeEvent.TRAILING_ACTIVATED: TradeStatus.TRAILING,
    TradeEvent.CLOSED: TradeStatus.CLOSED,
}

_ALLOWED: dict[TradeStatus, frozenset[TradeStatus]] = {
    TradeStatus.OPEN: frozenset({TradeStatus.BREAKEVEN, TradeStatus.TRAILING, TradeStatus.CLOSED}),
    TradeStatus.BREAKEVEN: frozenset({TradeStatus.TRAILING, TradeStatus.CLOSED}),
    TradeStatus.TRAILING: frozenset({TradeStatus.CLOSED}),
    TradeStatus.CLOSED: frozenset(),
}


class InvalidTransition(RuntimeError):
    pass


@dataclass
class PatternFeatures:
    regime: str | None = None
    score_components: dict | None = None
    filters_snapshot: dict | None = None
    hmm_state: str | None = None
    session: str | None = None


def can_transition(current: TradeStatus, event: TradeEvent) -> bool:
    if current == TradeStatus.CLOSED:
        return False
    target = _EVENT_TARGET[event]
    if target is None:
        return True
    return target in _ALLOWED[current]


def _write_pattern_on_close(db: Session, trade: Trade, features: PatternFeatures | None = None) -> Pattern:
    """Create a Pattern record from a closed trade for learning."""
    if trade.closed_at is None or trade.opened_at is None:
        raise ValueError("trade must have opened_at and closed_at to create pattern")

    if trade.pnl is None:
        raise ValueError("trade must have pnl to determine outcome")

    is_win = trade.pnl > 0
    outcome = "win" if is_win else ("loss" if trade.pnl < 0 else "breakeven")

    pattern = Pattern(
        trade_id=trade.id,
        features=features.filters_snapshot if features else trade.filters_snapshot,
        hmm_state=features.hmm_state if features else None,
        session=features.session if features else None,
        outcome=outcome,
        is_win=is_win,
    )
    db.add(pattern)
    db.flush()
    return pattern


def open_trade(
    db: Session,
    actor: ActorType = ActorType.AGENT,
    reason: str | None = None,
    **trade_fields,
) -> Trade:
    trade = Trade(status=TradeStatus.OPEN, **trade_fields)
    db.add(trade)
    db.add(AuditLog(actor=actor, action="trade_opened", reason=reason))
    db.flush()
    return trade


def apply_event(
    db: Session,
    trade: Trade,
    event: TradeEvent,
    actor: ActorType = ActorType.AGENT,
    reason: str | None = None,
    pattern_features: PatternFeatures | None = None,
) -> Trade:
    if not can_transition(trade.status, event):
        raise InvalidTransition(
            f"event '{event.value}' not allowed from status '{trade.status.value}'"
        )
    target = _EVENT_TARGET[event]
    if target is not None:
        trade.status = target
    if event == TradeEvent.CLOSED:
        if trade.closed_at is None:
            raise ValueError("trade.closed_at must be set before closing")
        _write_pattern_on_close(db, trade, pattern_features)
    db.add(AuditLog(actor=actor, action=f"trade_{event.value}", reason=reason))
    db.flush()
    return trade
