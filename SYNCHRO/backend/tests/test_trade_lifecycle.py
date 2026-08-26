import pytest

from synchro.db.models.system import ActorType, AuditLog
from synchro.db.models.trading import TradeDirection
from synchro.domain.audit import count_actions, record
from synchro.domain.trade_lifecycle import (
    InvalidTransition,
    TradeEvent,
    apply_event,
    can_transition,
    open_trade,
)


def _open(db, symbol="R_75"):
    return open_trade(
        db,
        account_id=1,
        symbol=symbol,
        direction=TradeDirection.BUY,
        lots=0.01,
        reason="5/5 score",
    )


def test_open_trade_creates_audit_entry(db_session):
    trade = _open(db_session)
    assert trade.status.value == "open"
    assert trade.closed_at is None
    assert count_actions(db_session, "trade_") == 1


def test_full_happy_path_ratchets_forward(db_session):
    from synchro.db.models.user import Account, User

    user = User(email="lifecycle@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    account = Account(user_id=user.id)
    db_session.add(account)
    db_session.flush()

    trade = open_trade(
        db_session,
        account_id=account.id,
        symbol="R_75",
        direction=TradeDirection.BUY,
        lots=0.01,
    )
    apply_event(db_session, trade, TradeEvent.PARTIAL_CLOSED, reason="TP1 50%")
    apply_event(
        db_session,
        trade,
        TradeEvent.BREAKEVEN_SET,
        actor=ActorType.SYSTEM,
        reason="+10 pips reached",
    )
    apply_event(db_session, trade, TradeEvent.TRAILING_ACTIVATED)
    apply_event(db_session, trade, TradeEvent.CLOSED, reason="SL hit in profit")

    assert trade.status.value == "closed"
    assert trade.closed_at is not None
    entries = list(db_session.query(AuditLog).order_by(AuditLog.id).all())
    actions = [e.action for e in entries]
    assert actions == [
        "trade_opened",
        "trade_partial_closed",
        "trade_breakeven_set",
        "trade_trailing_activated",
        "trade_closed",
    ]
    breakeven_entry = entries[2]
    assert breakeven_entry.actor == ActorType.SYSTEM


def test_backward_transitions_rejected(db_session):
    trade = _open(db_session)
    apply_event(db_session, trade, TradeEvent.BREAKEVEN_SET)

    with pytest.raises(InvalidTransition):
        apply_event(db_session, trade, TradeEvent.OPENED)

    apply_event(db_session, trade, TradeEvent.TRAILING_ACTIVATED)
    with pytest.raises(InvalidTransition):
        apply_event(db_session, trade, TradeEvent.BREAKEVEN_SET)

    assert trade.status.value == "trailing"


def test_terminal_state_locks_everything(db_session):
    trade = _open(db_session)
    apply_event(db_session, trade, TradeEvent.CLOSED)

    for event in TradeEvent:
        if event == TradeEvent.CLOSED:
            continue
        with pytest.raises(InvalidTransition):
            apply_event(db_session, trade, event)


def test_can_transition_table():
    assert can_transition("open", TradeEvent.BREAKEVEN_SET)
    assert can_transition("open", TradeEvent.TRAILING_ACTIVATED)
    assert can_transition("be", TradeEvent.TRAILING_ACTIVATED)
    assert not can_transition("trailing", TradeEvent.BREAKEVEN_SET)
    assert not can_transition("closed", TradeEvent.CLOSED)
