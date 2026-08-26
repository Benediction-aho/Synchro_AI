import enum

from sqlalchemy.orm import Session

from synchro.core.timeutils import utcnow
from synchro.db.models.system import ActorType, AuditLog
from synchro.db.models.trading import Trade, TradeStatus


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


def can_transition(current: TradeStatus, event: TradeEvent) -> bool:
    if current == TradeStatus.CLOSED:
        return False
    target = _EVENT_TARGET[event]
    if target is None:
        return True
    return target in _ALLOWED[current]


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
) -> Trade:
    if not can_transition(trade.status, event):
        raise InvalidTransition(
            f"event '{event.value}' not allowed from status '{trade.status.value}'"
        )
    target = _EVENT_TARGET[event]
    if target is not None:
        trade.status = target
    if event == TradeEvent.CLOSED and trade.closed_at is None:
        trade.closed_at = utcnow()
    db.add(AuditLog(actor=actor, action=f"trade_{event.value}", reason=reason))
    db.flush()
    return trade
