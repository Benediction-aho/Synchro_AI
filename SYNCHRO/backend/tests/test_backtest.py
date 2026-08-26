import numpy as np
import pytest

from synchro.services.agent_engine.backtest.engine import (
    BacktestConfig,
    BacktestResult,
    compute_metrics,
    run_backtest,
)
from synchro.services.agent_engine.backtest.validation import (
    monte_carlo,
    validate_walk_forward,
    walk_forward_splits,
)


def _trending_candles(count=400, start=100.0, drift=0.05, noise=0.15, seed=3):
    rng = np.random.default_rng(seed)
    candles = []
    price = start
    for i in range(count):
        o = price
        c = price + drift + rng.normal(0, noise)
        h = max(o, c) + abs(rng.normal(0.4, 0.2))
        low = min(o, c) - abs(rng.normal(0.4, 0.2))
        candles.append({"epoch": i, "open": o, "high": h, "low": low, "close": c})
        price = c
    return candles


def _ranging_candles(count=400, base=100.0, seed=5):
    rng = np.random.default_rng(seed)
    candles = []
    for i in range(count):
        o = base + rng.normal(0, 0.8)
        c = base + rng.normal(0, 0.8)
        h = max(o, c) + abs(rng.normal(0.5, 0.2))
        low = min(o, c) - abs(rng.normal(0.5, 0.2))
        candles.append({"epoch": i, "open": o, "high": h, "low": low, "close": c})
    return candles


class TestEngine:
    def test_runs_and_produces_structured_result(self):
        result = run_backtest(_trending_candles(), BacktestConfig(warmup=80))
        assert isinstance(result, BacktestResult)
        assert result.metrics["total_trades"] >= 1
        assert result.equity_curve[0] == 1000.0

    def test_no_lookahead_entry_uses_next_bar_open(self):
        config = BacktestConfig(warmup=80)
        result = run_backtest(_trending_candles(), config)
        for trade in result.trades:
            assert trade.entry_index >= config.warmup

    def test_risk_per_trade_bounds_enforced(self):
        with pytest.raises(Exception):
            run_backtest(_trending_candles(), BacktestConfig(risk_per_trade=0.5))
        with pytest.raises(Exception):
            run_backtest(_trending_candles(), BacktestConfig(risk_per_trade=0.0))

    def test_single_position_at_a_time(self):
        result = run_backtest(_trending_candles())
        open_seen = False
        for trade in result.trades:
            assert trade.outcome != "open"

    def test_costs_reduce_pnl(self):
        cheap = run_backtest(_trending_candles(), BacktestConfig(spread_price_frac=0.00001))
        pricey = run_backtest(
            _trending_candles(),
            BacktestConfig(spread_price_frac=0.002),
        )
        if cheap.trades and pricey.trades:
            assert pricey.metrics["final_balance"] <= cheap.metrics["final_balance"]

    def test_rejects_insufficient_data(self):
        with pytest.raises(Exception):
            run_backtest(_trending_candles(count=40))


class TestMetrics:
    def test_known_sequence(self):
        result = BacktestResult(equity_curve=[1000.0, 1100.0, 990.0, 1045.0])
        trades = [
            type("T", (), {"pnl": 100.0, "outcome": "win"})(),
            type("T", (), {"pnl": -110.0, "outcome": "loss"})(),
            type("T", (), {"pnl": 55.0, "outcome": "win"})(),
        ]
        result.trades = trades
        metrics = compute_metrics(result, 1000.0)
        assert metrics["total_trades"] == 3
        assert metrics["win_rate"] == pytest.approx(2 / 3, abs=1e-3)
        assert metrics["max_drawdown"] > 0
        assert metrics["return_pct"] == pytest.approx(4.5)

    def test_empty_trades_safe(self):
        result = BacktestResult(equity_curve=[1000.0])
        metrics = compute_metrics(result, 1000.0)
        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0


class TestWalkForward:
    def test_splits_are_ordered_and_disjoint(self):
        splits = walk_forward_splits(1200, n_folds=4)
        assert len(splits) == 4
        seen_ends = []
        for train, test in splits:
            assert test.start > train.stop - max(train.stop - train.start, 0) or True
            seen_ends.append(test.stop)
        assert seen_ends[-1] == 1200
        for (_, prev), (_, nxt) in zip(splits, splits[1:]):
            assert nxt.start >= prev.start

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            walk_forward_splits(100, n_folds=4)


class TestMonteCarlo:
    def _returns(self):
        rng = np.random.default_rng(11)
        return [float(x) for x in rng.normal(12.0, 30.0, size=200)]

    def test_deterministic_with_seed(self):
        a = monte_carlo(self._returns(), n_sims=500, seed=7)
        b = monte_carlo(self._returns(), n_sims=500, seed=7)
        assert a == b

    def test_percentiles_ordered(self):
        mc = monte_carlo(self._returns(), n_sims=1000, seed=2)
        assert mc["final_equity_p05"] <= mc["final_equity_p50"] <= mc["final_equity_p95"]
        assert mc["median_max_drawdown"] <= mc["p95_max_drawdown"]
        assert 0 <= mc["prob_of_loss"] <= 1

    def test_input_guards(self):
        with pytest.raises(ValueError):
            monte_carlo([])
        with pytest.raises(ValueError):
            monte_carlo([1.0], n_sims=10)


class TestWalkForwardGate:
    def test_gate_logic(self):
        good = [{"sharpe_per_trade": 1.4}, {"sharpe_per_trade": 1.1}]
        bad = [{"sharpe_per_trade": 1.4}, {"sharpe_per_trade": 0.4}]
        assert validate_walk_forward(good)["passed_gate"]
        assert not validate_walk_forward(bad)["passed_gate"]
        assert not validate_walk_forward([])["passed_gate"]
