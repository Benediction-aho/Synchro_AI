"""Walk-forward validation and Monte Carlo robustness checks (Doc 5)."""

from typing import Any

import numpy as np

from synchro.services.agent_engine.backtest.engine import BacktestResult, compute_metrics


def walk_forward_splits(
    total_bars: int, n_folds: int = 4, train_fraction: float = 0.6, min_test: int = 50
) -> list[tuple[range, range]]:
    """Expanding-window folds: train grows, test windows are disjoint."""
    if total_bars < min_test * n_folds + 20:
        raise ValueError(f"need >= {min_test * n_folds + 20} bars for {n_folds} folds")
    if not 0.2 <= train_fraction <= 0.9:
        raise ValueError("train_fraction must be in [0.2, 0.9]")
    test_size = (total_bars - int(total_bars * train_fraction)) // n_folds
    splits = []
    train_end = int(total_bars * train_fraction)
    for k in range(n_folds):
        test_start = train_end + k * test_size
        test_end = test_start + test_size
        if k == n_folds - 1:
            test_end = total_bars
        splits.append((range(0, train_end + k * test_size), range(test_start, test_end)))
    return splits


def monte_carlo(
    trade_returns: list[float],
    n_sims: int = 10_000,
    initial_balance: float = 1_000.0,
    seed: int = 42,
) -> dict[str, float]:
    """Bootstrap-resample per-trade PnL to estimate drawdown/final-equity risk."""
    if not trade_returns:
        raise ValueError("monte carlo needs at least one trade return")
    if n_sims < 100 or n_sims > 1_000_000:
        raise ValueError("n_sims must be in [100, 1000000]")
    rng = np.random.default_rng(seed)
    returns = np.array(trade_returns, dtype=float)
    n = returns.size
    finals = np.empty(n_sims)
    max_dds = np.empty(n_sims)

    for s in range(n_sims):
        sample = returns[rng.integers(0, n, size=n)]
        equity = initial_balance + np.cumsum(sample)
        peak = np.maximum.accumulate(equity)
        max_dds[s] = float(((peak - equity) / peak).max())
        finals[s] = equity[-1]

    return {
        "final_equity_p05": round(float(np.percentile(finals, 5)), 2),
        "final_equity_p50": round(float(np.percentile(finals, 50)), 2),
        "final_equity_p95": round(float(np.percentile(finals, 95)), 2),
        "median_max_drawdown": round(float(np.median(max_dds)), 4),
        "p95_max_drawdown": round(float(np.percentile(max_dds, 95)), 4),
        "prob_of_loss": round(float((finals < initial_balance).mean()), 4),
    }


def validate_walk_forward(results: list[dict[str, Any]], min_sharpe: float = 1.0) -> dict[str, Any]:
    """Doc 5 gate: walk-forward Sharpe > 1.0 on out-of-sample data."""
    sharpes = [r.get("sharpe_per_trade", 0.0) for r in results]
    passed = bool(sharpes) and all(s > min_sharpe for s in sharpes)
    return {
        "fold_sharpes": [round(s, 4) for s in sharpes],
        "passed_gate": passed,
        "gate_threshold": min_sharpe,
    }
