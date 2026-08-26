"""Tests for learning worker nightly job."""

import pytest
from datetime import datetime, timezone

from synchro.services.learning_worker.tasks import (
    _win_rate_by_symbol,
    _kelly_fraction,
    _kelly_per_account,
    _threshold_recommendations,
    manual_learning_job,
)
from synchro.db.models.trading import Trade, TradeDirection, TradeStatus
from synchro.db.models.learning import Pattern
from synchro.db.models.user import User, Account
from synchro.core.security import hash_password
from synchro.core.timeutils import utcnow


class TestWinRateBySymbol:
    def _setup_account_with_trades(self, db_session):
        user = User(email="wr@example.com", password_hash=hash_password("x"), is_active=True)
        db_session.add(user)
        db_session.flush()
        account = Account(user_id=user.id, is_active=True)
        db_session.add(account)
        db_session.flush()

        # Create closed trades with known outcomes
        trades_data = [
            ("R_75", 100.0, True),
            ("R_75", 50.0, True),
            ("R_75", -30.0, False),
            ("R_100", 20.0, True),
            ("R_100", -10.0, False),
        ]
        for symbol, pnl, is_win in trades_data:
            trade = Trade(
                account_id=account.id,
                symbol=symbol,
                direction=TradeDirection.BUY,
                entry_price=100.0,
                exit_price=100.0 + pnl,
                pnl=pnl,
                lots=0.1,
                status=TradeStatus.CLOSED,
                closed_at=utcnow(),
            )
            db_session.add(trade)
        db_session.flush()
        return account.id

    def test_win_rate_calculation(self, db_session):
        account_id = self._setup_account_with_trades(db_session)
        wr = _win_rate_by_symbol(db_session, account_id)

        assert "R_75" in wr
        assert wr["R_75"]["total_trades"] == 3
        assert wr["R_75"]["win_rate"] == pytest.approx(2 / 3)

        assert "R_100" in wr
        assert wr["R_100"]["total_trades"] == 2
        assert wr["R_100"]["win_rate"] == 0.5


class TestKellyFraction:
    def test_kelly_positive_edge(self):
        # 60% win rate, avg win 2x avg loss -> kelly = 0.6 - 0.4/2 = 0.4, capped at 0.25
        k = _kelly_fraction(0.6, 2.0, 1.0)
        assert k == 0.25

    def test_kelly_zero_when_no_edge(self):
        # 50% win rate, 1:1 -> kelly = 0
        k = _kelly_fraction(0.5, 1.0, 1.0)
        assert k == 0.0

    def test_kelly_capped_at_25_pct(self):
        # Very high edge -> should cap at 0.25
        k = _kelly_fraction(0.9, 10.0, 1.0)
        assert k == 0.25

    def test_kelly_invalid_inputs(self):
        assert _kelly_fraction(0.0, 1.0, 1.0) == 0.0
        assert _kelly_fraction(1.0, 1.0, 1.0) == 0.0
        assert _kelly_fraction(0.5, 1.0, 0.0) == 0.0


class TestKellyPerAccount:
    def _setup_account(self, db_session):
        user = User(email="kelly@example.com", password_hash=hash_password("x"), is_active=True)
        db_session.add(user)
        db_session.flush()
        account = Account(user_id=user.id, is_active=True)
        db_session.add(account)
        db_session.flush()

        # Create closed trades
        pnls = [100, 50, -30, 20, -10, 40, -20]
        for pnl in pnls:
            trade = Trade(
                account_id=account.id,
                symbol="R_75",
                direction=TradeDirection.BUY,
                entry_price=100.0,
                exit_price=100.0 + pnl,
                pnl=pnl,
                lots=0.1,
                status=TradeStatus.CLOSED,
                closed_at=utcnow(),
            )
            db_session.add(trade)
        db_session.flush()
        return account.id

    def test_kelly_computation(self, db_session):
        account_id = self._setup_account(db_session)
        k = _kelly_per_account(db_session, account_id)
        assert 0.0 <= k <= 0.25


class TestThresholdRecommendations:
    def _setup_account_with_patterns(self, db_session):
        user = User(email="thresh@example.com", password_hash=hash_password("x"), is_active=True)
        db_session.add(user)
        db_session.flush()
        account = Account(user_id=user.id, is_active=True)
        db_session.add(account)
        db_session.flush()

        # Create trade with pattern
        trade = Trade(
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            pnl=50.0,
            lots=0.1,
            status=TradeStatus.CLOSED,
            closed_at=utcnow(),
            filters_snapshot={"regime_allowed": True, "min_atr": True},
        )
        db_session.add(trade)
        db_session.flush()

        pattern = Pattern(
            trade_id=trade.id,
            features={"regime_allowed": True, "min_atr": True},
            is_win=True,
        )
        db_session.add(pattern)
        db_session.flush()

        return account.id

    def test_recommendations_structure(self, db_session):
        account_id = self._setup_account_with_patterns(db_session)
        recs = _threshold_recommendations(db_session, account_id)

        assert "min_score" in recs
        assert "filter_adjustments" in recs


class TestManualLearningJob:
    def _setup_account(self, db_session):
        user = User(email="manual@example.com", password_hash=hash_password("x"), is_active=True)
        db_session.add(user)
        db_session.flush()
        account = Account(user_id=user.id, is_active=True)
        db_session.add(account)
        db_session.flush()

        trade = Trade(
            account_id=account.id,
            symbol="R_75",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            pnl=50.0,
            lots=0.1,
            status=TradeStatus.CLOSED,
            closed_at=utcnow(),
        )
        db_session.add(trade)
        db_session.flush()
        return account.id

    def test_returns_structured_result(self, db_session):
        account_id = self._setup_account(db_session)
        result = manual_learning_job(account_id)

        assert result["status"] == "ok"
        assert result["account_id"] == account_id
        assert "win_rates" in result
        assert "kelly_fraction" in result
        assert "threshold_recommendations" in result
        assert "computed_at" in result