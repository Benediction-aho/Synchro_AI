import pytest
from datetime import datetime, timezone

from synchro.core.timeutils import utcnow
from synchro.domain.trade_lifecycle import (
    TradeEvent,
    TradeStatus,
    InvalidTransition,
    can_transition,
    open_trade,
    apply_event,
    PatternFeatures,
)
from synchro.db.models.trading import Trade, TradeDirection
from synchro.db.models.learning import Pattern
from synchro.db.models.user import User, Account
from synchro.core.security import hash_password


class TestTradeLifecyclePatternWrite:
    def _make_user_account(self, db_session):
        user = User(email="test@example.com", password_hash=hash_password("secret"), is_active=True)
        db_session.add(user)
        db_session.flush()
        account = Account(user_id=user.id, is_active=True)
        db_session.add(account)
        db_session.flush()
        return user, account

    def test_pattern_created_on_close(self, db_session):
        _, account = self._make_user_account(db_session)

        trade = open_trade(
            db_session,
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            sl_initial=95.0,
            tp=110.0,
            lots=0.1,
        )
        db_session.flush()

        trade.pnl = 50.0
        trade.exit_price = 105.0
        trade.closed_at = utcnow()
        apply_event(db_session, trade, TradeEvent.CLOSED, pattern_features=PatternFeatures(
            regime="trend_up",
            score_components={"regime": 1, "trend": 1, "momentum": 1, "structure": 1, "trigger": 1},
            filters_snapshot={"regime_allowed": True, "min_atr": True},
            hmm_state="trend_up",
            session="london",
        ))

        patterns = db_session.query(Pattern).filter(Pattern.trade_id == trade.id).all()
        assert len(patterns) == 1
        p = patterns[0]
        assert p.trade_id == trade.id
        assert p.is_win is True
        assert p.outcome == "win"
        assert p.hmm_state == "trend_up"
        assert p.session == "london"
        assert p.features["regime_allowed"] is True

    def test_pattern_created_on_loss(self, db_session):
        _, account = self._make_user_account(db_session)

        trade = open_trade(
            db_session,
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.SELL,
            entry_price=100.0,
            sl_initial=105.0,
            tp=90.0,
            lots=0.1,
        )
        db_session.flush()

        trade.pnl = -30.0
        trade.exit_price = 103.0
        trade.closed_at = utcnow()
        apply_event(db_session, trade, TradeEvent.CLOSED, pattern_features=PatternFeatures(
            regime="range",
            hmm_state="range",
        ))

        patterns = db_session.query(Pattern).filter(Pattern.trade_id == trade.id).all()
        assert len(patterns) == 1
        p = patterns[0]
        assert p.is_win is False
        assert p.outcome == "loss"
        assert p.hmm_state == "range"

    def test_pattern_created_on_breakeven(self, db_session):
        _, account = self._make_user_account(db_session)

        trade = open_trade(
            db_session,
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            sl_initial=95.0,
            tp=110.0,
            lots=0.1,
        )
        db_session.flush()

        trade.pnl = 0.0
        trade.exit_price = 100.0
        trade.closed_at = utcnow()
        apply_event(db_session, trade, TradeEvent.CLOSED)

        patterns = db_session.query(Pattern).filter(Pattern.trade_id == trade.id).all()
        assert len(patterns) == 1
        assert patterns[0].outcome == "breakeven"
        assert patterns[0].is_win is False  # breakeven is not a win

    def test_pattern_requires_pnl(self, db_session):
        _, account = self._make_user_account(db_session)

        trade = open_trade(
            db_session,
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            sl_initial=95.0,
            tp=110.0,
            lots=0.1,
        )
        db_session.flush()

        # No pnl set - should fail
        trade.exit_price = 105.0
        trade.closed_at = utcnow()
        with pytest.raises(ValueError, match="pnl"):
            apply_event(db_session, trade, TradeEvent.CLOSED)

    def test_pattern_requires_closed_at(self, db_session):
        _, account = self._make_user_account(db_session)

        trade = open_trade(
            db_session,
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            sl_initial=95.0,
            tp=110.0,
            lots=0.1,
        )
        db_session.flush()

        trade.pnl = 50.0
        trade.exit_price = 105.0
        trade.closed_at = None  # explicitly remove

        with pytest.raises(ValueError, match="trade.closed_at must be set before closing"):
            apply_event(db_session, trade, TradeEvent.CLOSED)

    def test_no_duplicate_pattern_on_double_close(self, db_session):
        _, account = self._make_user_account(db_session)

        trade = open_trade(
            db_session,
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            sl_initial=95.0,
            tp=110.0,
            lots=0.1,
        )
        db_session.flush()

        trade.pnl = 50.0
        trade.exit_price = 105.0
        trade.closed_at = utcnow()
        apply_event(db_session, trade, TradeEvent.CLOSED)

        # Second close should not create another pattern (status is CLOSED)
        trade.pnl = 60.0
        with pytest.raises(InvalidTransition):
            apply_event(db_session, trade, TradeEvent.CLOSED)

        patterns = db_session.query(Pattern).filter(Pattern.trade_id == trade.id).all()
        assert len(patterns) == 1

    def test_pattern_features_fallback_to_trade_fields(self, db_session):
        """When pattern_features not provided, falls back to trade's filters_snapshot."""
        _, account = self._make_user_account(db_session)

        trade = open_trade(
            db_session,
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            sl_initial=95.0,
            tp=110.0,
            lots=0.1,
            filters_snapshot={"fallback": True},
        )
        db_session.flush()

        trade.pnl = 10.0
        trade.exit_price = 101.0
        trade.closed_at = utcnow()
        apply_event(db_session, trade, TradeEvent.CLOSED)  # no pattern_features

        pattern = db_session.query(Pattern).filter(Pattern.trade_id == trade.id).first()
        assert pattern.features["fallback"] is True

    def test_lifecycle_transitions_still_work(self, db_session):
        """Ensure existing transitions still work with new signature."""
        _, account = self._make_user_account(db_session)

        trade = open_trade(db_session, account_id=account.id, symbol="R_75",
            direction=TradeDirection.BUY, entry_price=100.0, sl_initial=95.0, tp=110.0, lots=0.1)
        assert trade.status == TradeStatus.OPEN

        apply_event(db_session, trade, TradeEvent.BREAKEVEN_SET)
        assert trade.status == TradeStatus.BREAKEVEN

        apply_event(db_session, trade, TradeEvent.TRAILING_ACTIVATED)
        assert trade.status == TradeStatus.TRAILING

        trade.pnl = 20.0
        trade.exit_price = 102.0
        trade.closed_at = utcnow()
        apply_event(db_session, trade, TradeEvent.CLOSED)
        assert trade.status == TradeStatus.CLOSED


class TestCanTransition:
    def test_open_to_breakeven(self):
        assert can_transition(TradeStatus.OPEN, TradeEvent.BREAKEVEN_SET)

    def test_open_to_trailing(self):
        assert can_transition(TradeStatus.OPEN, TradeEvent.TRAILING_ACTIVATED)

    def test_open_to_closed(self):
        assert can_transition(TradeStatus.OPEN, TradeEvent.CLOSED)

    def test_breakeven_to_trailing(self):
        assert can_transition(TradeStatus.BREAKEVEN, TradeEvent.TRAILING_ACTIVATED)

    def test_breakeven_to_closed(self):
        assert can_transition(TradeStatus.BREAKEVEN, TradeEvent.CLOSED)

    def test_trailing_to_closed(self):
        assert can_transition(TradeStatus.TRAILING, TradeEvent.CLOSED)

    def test_closed_no_transitions(self):
        for e in TradeEvent:
            assert not can_transition(TradeStatus.CLOSED, e)

    def test_partial_close_no_status_change(self):
        assert can_transition(TradeStatus.OPEN, TradeEvent.PARTIAL_CLOSED)
        assert can_transition(TradeStatus.BREAKEVEN, TradeEvent.PARTIAL_CLOSED)
        assert can_transition(TradeStatus.TRAILING, TradeEvent.PARTIAL_CLOSED)