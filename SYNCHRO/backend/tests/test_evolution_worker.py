"""Tests for evolution worker."""

import pytest
from datetime import date

from synchro.services.evolution_worker.tasks import (
    _generate_variations,
    _select_winner,
    PARAM_SPACE,
    manual_evolution_cycle,
)
from synchro.db.models.trading import Trade, TradeDirection, TradeStatus
from synchro.db.models.user import User, Account
from synchro.core.security import hash_password
from synchro.core.timeutils import utcnow


class TestGenerateVariations:
    def test_generates_correct_count(self):
        base = {k: v["current"] for k, v in PARAM_SPACE.items()}
        variations = _generate_variations(base, n=5)
        assert len(variations) == 5

    def test_variations_differ_from_base(self):
        base = {k: v["current"] for k, v in PARAM_SPACE.items()}
        variations = _generate_variations(base, n=10)
        # At least some should differ
        diffs = sum(1 for v in variations if v != base)
        assert diffs > 0

    def test_variations_within_bounds(self):
        base = {k: v["current"] for k, v in PARAM_SPACE.items()}
        variations = _generate_variations(base, n=50)
        for v in variations:
            assert 3 <= v["min_score"] <= 5
            assert 0.001 <= v["min_atr_pct"] <= 0.02
            assert 0.005 <= v["risk_per_trade"] <= 0.02
            assert 1.0 <= v["rr_multiple"] <= 3.0
            assert isinstance(v["regime_filter_enabled"], bool)


class TestSelectWinner:
    def test_selects_highest_sharpe(self):
        results = [
            {"sharpe_per_trade": 1.0, "win_rate": 0.5, "profit_factor": 1.2, "total_trades": 20},
            {"sharpe_per_trade": 1.5, "win_rate": 0.45, "profit_factor": 1.1, "total_trades": 15},
            {"sharpe_per_trade": 0.8, "win_rate": 0.6, "profit_factor": 1.5, "total_trades": 25},
        ]
        winner = _select_winner(results)
        assert winner["sharpe_per_trade"] == 1.5

    def test_tiebreaks_on_win_rate(self):
        results = [
            {"sharpe_per_trade": 1.5, "win_rate": 0.5, "profit_factor": 1.2, "total_trades": 20},
            {"sharpe_per_trade": 1.5, "win_rate": 0.6, "profit_factor": 1.1, "total_trades": 15},
        ]
        winner = _select_winner(results)
        assert winner["win_rate"] == 0.6

    def test_filters_insufficient_trades(self):
        results = [
            {"sharpe_per_trade": 2.0, "win_rate": 0.8, "profit_factor": 3.0, "total_trades": 5},
            {"sharpe_per_trade": 1.0, "win_rate": 0.5, "profit_factor": 1.2, "total_trades": 20},
        ]
        winner = _select_winner(results)
        assert winner["total_trades"] == 20

    def test_returns_none_for_empty(self):
        assert _select_winner([]) is None

    def test_returns_none_when_all_insufficient(self):
        results = [
            {"sharpe_per_trade": 2.0, "win_rate": 0.8, "profit_factor": 3.0, "total_trades": 3},
            {"sharpe_per_trade": 1.5, "win_rate": 0.6, "profit_factor": 1.5, "total_trades": 5},
        ]
        assert _select_winner(results) is None


class TestManualEvolutionCycle:
    def _setup_account(self, db_session):
        user = User(email="evo@example.com", password_hash=hash_password("x"), is_active=True)
        db_session.add(user)
        db_session.flush()
        account = Account(user_id=user.id, is_active=True)
        db_session.add(account)
        db_session.flush()

        # Create some closed trades for backtesting
        for i in range(200):
            trade = Trade(
                account_id=account.id,
                symbol="R_75",
                direction=TradeDirection.BUY,
                entry_price=100.0 + i * 0.01,
                pnl=5.0 if i % 3 == 0 else -3.0,
                lots=0.1,
                status=TradeStatus.CLOSED,
                closed_at=utcnow(),
            )
            db_session.add(trade)
        db_session.flush()
        return account.id

    def test_returns_structured_result(self, db_session):
        account_id = self._setup_account(db_session)
        result = manual_evolution_cycle(account_id)

        assert result["status"] == "ok"
        assert result["account_id"] == account_id
        assert "variations_tested" in result
        assert "winner" in result
        assert "all_results" in result
        assert isinstance(result["all_results"], list)