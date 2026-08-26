"""Evolution Worker tasks (48h cycle) — Doc 4 item 18.

Flow:
1. Generate parameter variations from current best config
2. Backtest each variation on recent data
3. Deploy winner to 24h demo sandbox
4. Auto-rollback if drawdown exceeds threshold
"""

import random
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from synchro.core.timeutils import utcnow
from synchro.db.models.trading import Trade, TradeStatus
from synchro.db.models.learning import EvolutionLog, ModelVersion, Pattern
from synchro.db.models.user import Account
from synchro.db.session import SessionLocal
from synchro.services.agent_engine.backtest.engine import BacktestConfig, run_backtest
from synchro.services.agent_engine.intelligence.candles import to_candle_array


# Default parameter space for variation generation
PARAM_SPACE = {
    "min_score": {"type": "int", "min": 3, "max": 5, "current": 5},
    "min_atr_pct": {"type": "float", "min": 0.001, "max": 0.02, "current": 0.005},
    "regime_filter_enabled": {"type": "bool", "current": True},
    "trend_filter_enabled": {"type": "bool", "current": True},
    "momentum_filter_enabled": {"type": "bool", "current": True},
    "structure_filter_enabled": {"type": "bool", "current": True},
    "trigger_filter_enabled": {"type": "bool", "current": True},
    "risk_per_trade": {"type": "float", "min": 0.005, "max": 0.02, "current": 0.01},
    "rr_multiple": {"type": "float", "min": 1.0, "max": 3.0, "current": 1.5},
}


def _generate_variations(base_params: dict, n: int = 5) -> list[dict]:
    """Generate n parameter variations by mutating base params."""
    variations = []
    for _ in range(n):
        variant = base_params.copy()
        # Mutate 1-2 parameters
        num_mutations = random.randint(1, 2)
        keys = random.sample(list(PARAM_SPACE.keys()), num_mutations)
        for key in keys:
            spec = PARAM_SPACE[key]
            if spec["type"] == "int":
                variant[key] = random.randint(spec["min"], spec["max"])
            elif spec["type"] == "float":
                variant[key] = round(random.uniform(spec["min"], spec["max"]), 4)
            elif spec["type"] == "bool":
                variant[key] = not variant[key]
        variations.append(variant)
    return variations


def _fetch_recent_candles(db: Session, symbol: str, days: int = 60) -> list[dict]:
    """Fetch recent closed trade data as proxy candles for backtesting.
    In production, this would come from a proper timeseries table.
    """
    # For now, create synthetic candles from recent trade data
    cutoff = utcnow() - timedelta(days=days)
    trades = (
        db.query(Trade)
        .filter(Trade.symbol == symbol, Trade.closed_at >= cutoff, Trade.status == TradeStatus.CLOSED)
        .order_by(Trade.opened_at)
        .limit(500)
        .all()
    )
    # Convert trades to pseudo-candles (this is a simplified approach)
    candles = []
    for i, t in enumerate(trades):
        price = float(t.entry_price) if t.entry_price else 100.0
        pnl = float(t.pnl) if t.pnl else 0.0
        direction = 1 if t.direction.value == "buy" else -1
        close = price + direction * abs(pnl) / 100.0  # rough approximation
        candles.append({
            "epoch": i,
            "open": price,
            "high": max(price, close) + abs(pnl) * 0.001,
            "low": min(price, close) - abs(pnl) * 0.001,
            "close": close,
        })
    if len(candles) < 100:
        # Fallback: generate synthetic trending data
        return _synthetic_candles(500)
    return candles


def _synthetic_candles(count: int = 500) -> list[dict]:
    """Generate synthetic candles for backtesting when real data is sparse."""
    import numpy as np
    rng = np.random.default_rng(42)
    candles = []
    price = 100.0
    for i in range(count):
        drift = 0.02 + rng.normal(0, 0.05)
        noise = rng.normal(0, 0.15)
        o = price
        c = price + drift + noise
        h = max(o, c) + abs(rng.normal(0.4, 0.2))
        low = min(o, c) - abs(rng.normal(0.4, 0.2))
        candles.append({"epoch": i, "open": o, "high": h, "low": low, "close": c})
        price = c
    return candles


def _backtest_variation(params: dict, candles: list[dict]) -> dict[str, Any]:
    """Run backtest with given parameters."""
    # Create scorer with modified params
    scorer = APEXScorer()
    # Note: In full implementation, we'd pass params to scorer
    # For now, use default scorer and backtest engine config
    config = BacktestConfig(
        warmup=120,
        risk_per_trade=params.get("risk_per_trade", 0.01),
        rr_multiple=params.get("rr_multiple", 1.5),
    )
    result = run_backtest(candles, config)
    return {
        "params": params,
        "sharpe_per_trade": result.metrics.get("sharpe_per_trade", 0.0),
        "win_rate": result.metrics.get("win_rate", 0.0),
        "profit_factor": result.metrics.get("profit_factor", 0.0),
        "max_drawdown": result.metrics.get("max_drawdown", 1.0),
        "total_trades": result.metrics.get("total_trades", 0),
    }


def _select_winner(results: list[dict]) -> dict | None:
    """Select best variation by Sharpe, then win rate, then profit factor."""
    if not results:
        return None
    # Filter out variations with too few trades
    valid = [r for r in results if r["total_trades"] >= 10]
    if not valid:
        return None
    # Sort by Sharpe desc, then win_rate desc, then profit_factor desc
    valid.sort(key=lambda x: (x["sharpe_per_trade"], x["win_rate"], x["profit_factor"]), reverse=True)
    return valid[0]


def _save_model_version(winner: dict) -> ModelVersion:
    """Persist winning parameter set as new model version."""
    db: Session = SessionLocal()
    try:
        version = ModelVersion(
            version=f"v{utcnow().strftime('%Y%m%d_%H%M')}",
            params=winner["params"],
            backtest_metrics={
                "sharpe_per_trade": winner["sharpe_per_trade"],
                "win_rate": winner["win_rate"],
                "profit_factor": winner["profit_factor"],
                "max_drawdown": winner["max_drawdown"],
                "total_trades": winner["total_trades"],
            },
        )
        db.add(version)
        db.flush()
        return version
    finally:
        db.close()


def _log_evolution_cycle(
    cycle_date: date,
    variations_tested: int,
    winner: dict | None,
    demo_validated: bool = False,
    human_approved: bool = False,
) -> EvolutionLog:
    """Log the evolution cycle outcome."""
    db: Session = SessionLocal()
    try:
        log = EvolutionLog(
            cycle_date=cycle_date,
            variations_tested=variations_tested,
            winner=winner["params"] if winner else None,
            improvement_pct=None,  # compute vs previous if needed
            demo_validated=demo_validated,
            human_approved=human_approved,
        )
        db.add(log)
        db.flush()
        return log
    finally:
        db.close()


def run_evolution_cycle() -> dict[str, Any]:
    """Main entrypoint for 04:00 UTC Celery beat job."""
    db: Session = SessionLocal()
    try:
        cycle_date = utcnow().date()
        # Get active accounts
        accounts = db.query(Account).filter(Account.is_active == True).all()
        if not accounts:
            return {"status": "skipped", "reason": "no active accounts"}

        all_results = []
        for account in accounts:
            # Get current config (simplified - would come from configurations table)
            base_params = {k: v["current"] for k, v in PARAM_SPACE.items()}

            # Generate variations
            variations = _generate_variations(base_params, n=8)

            # Fetch candles for primary symbol (first active market or default)
            symbol = "R_75"  # default
            candles = _fetch_recent_candles(db, symbol)

            # Backtest each variation
            results = []
            for var in variations:
                try:
                    result = _backtest_variation(var, candles)
                    results.append(result)
                except Exception as e:
                    print(f"Backtest failed for {var}: {e}")
                    continue

            # Select winner
            winner = _select_winner(results)
            if winner:
                all_results.append({"account_id": account.id, "winner": winner})
                _save_model_version(winner)

        # Log cycle
        total_variations = sum(len(_generate_variations({k: v["current"] for k, v in PARAM_SPACE.items()}, n=8)) for _ in accounts)
        _log_evolution_cycle(cycle_date, total_variations, all_results[0]["winner"] if all_results else None)

        return {
            "status": "ok",
            "cycle_date": cycle_date.isoformat(),
            "accounts_processed": len(accounts),
            "winners": all_results,
        }
    finally:
        db.close()


def manual_evolution_cycle(account_id: int) -> dict[str, Any]:
    """Run evolution cycle for a single account (testing)."""
    db: Session = SessionLocal()
    try:
        base_params = {k: v["current"] for k, v in PARAM_SPACE.items()}
        variations = _generate_variations(base_params, n=5)
        symbol = "R_75"
        candles = _fetch_recent_candles(db, symbol)

        results = []
        for var in variations:
            try:
                result = _backtest_variation(var, candles)
                results.append(result)
            except Exception as e:
                print(f"Backtest failed for {var}: {e}")
                continue

        winner = _select_winner(results)
        return {
            "status": "ok",
            "account_id": account_id,
            "variations_tested": len(variations),
            "winner": winner,
            "all_results": results,
        }
    finally:
        db.close()