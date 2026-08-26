from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from synchro.core.timeutils import utcnow
from synchro.db.models.billing import Plan, Subscription, SubscriptionStatus
from synchro.db.models.learning import Pattern, QValue
from synchro.db.models.system import Alert, AlertType
from synchro.db.models.trading import (
    Configuration,
    EquitySnapshot,
    Signal,
    SignalDecision,
    Trade,
    TradeDirection,
    TradeStatus,
)
from synchro.db.models.user import Account, ApiCredential, AccountType, User


def _make_user(db):
    user = User(email="model-test@example.com", password_hash="x")
    db.add(user)
    db.flush()
    return user


def test_full_relationship_chain(db_session):
    user = _make_user(db_session)

    account = Account(user_id=user.id, name="deriv-demo")
    db_session.add(account)
    db_session.flush()

    config = Configuration(account_id=account.id, allocated_capital=1000, active_markets=["V75"])
    trade = Trade(
        account_id=account.id,
        symbol="V75",
        direction=TradeDirection.BUY,
        lots=0.01,
        entry_price=10500.5,
        sl_initial=10480.0,
        tp=10550.0,
        status=TradeStatus.OPEN,
        score_components={"trend": 1, "momentum": 1},
    )
    signal = Signal(
        account_id=account.id,
        symbol="V75",
        apex_layer_results={"regime": "trending"},
        decision=SignalDecision.BUY,
        reason_text="5/5 score reached",
    )
    snapshot_kwargs = dict(account_id=account.id, timestamp=utcnow())
    snapshot = EquitySnapshot(**snapshot_kwargs, balance=1000, equity=1015.5, daily_pnl=15.5)
    credential = ApiCredential(
        user_id=user.id,
        account_id=account.id,
        account_type=AccountType.DEMO,
        account_login="MQL12345",
    )
    subscription = Subscription(user_id=user.id, plan=Plan.FREE, status=SubscriptionStatus.ACTIVE)
    alert = Alert(
        user_id=user.id,
        type=AlertType.APPROVAL,
        payload={"symbol": "V75"},
        expires_at=utcnow() + timedelta(minutes=15),
    )
    qv = QValue(state_key="trend|london|r3", action="buy", q_value=0.42)
    db_session.add_all([config, trade, signal, snapshot, credential, subscription, alert, qv])
    db_session.flush()

    pattern = Pattern(trade_id=trade.id, features={"bos": True}, hmm_state="trending", session="london")
    db_session.add(pattern)
    db_session.commit()

    assert config.min_score == 5
    assert config.risk_phase == 0
    assert account.configuration.min_score == 5
    assert len(account.trades) == 1
    assert trade.patterns[0].hmm_state == "trending"
    assert signal.decision.value == "BUY"
    assert account.equity_snapshots[0].equity == 1015.5
    assert credential.account_type == AccountType.DEMO
    assert alert.type == AlertType.APPROVAL
    assert alert.response is None
    assert qv.q_value == 0.42


def test_risk_phase_check_constraint(db_session):
    user = _make_user(db_session)
    account = Account(user_id=user.id)
    db_session.add(account)
    db_session.flush()
    config = Configuration(account_id=account.id, risk_phase=7)
    db_session.add(config)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_email_constraint(db_session):
    _make_user(db_session)
    duplicate = User(email="model-test@example.com", password_hash="y")
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
