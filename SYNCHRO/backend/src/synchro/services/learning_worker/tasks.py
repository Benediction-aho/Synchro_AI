"""Nightly learning worker tasks (02:00 UTC) — Doc 4 item 17.

Computes:
- Win rate per symbol
- Kelly fraction per account
- Threshold adjustment recommendations
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from synchro.core.timeutils import utcnow
from synchro.db.models.trading import Trade, TradeStatus
from synchro.db.models.learning import Pattern
from synchro.db.models.user import Account
from synchro.db.session import SessionLocal


def _win_rate_by_symbol(db: Session, account_id: int, days: int = 30) -> dict[str, dict]:
    """Win rate per symbol for last N days."""
    cutoff = utcnow() - timedelta(days=days)
    win_case = case((Trade.pnl > 0, 1), else_=0)
    rows = (
        db.query(
            Trade.symbol,
            func.count(Trade.id).label("total"),
            func.sum(win_case).label("wins"),
            func.avg(Trade.pnl).label("avg_pnl"),
        )
        .filter(Trade.account_id == account_id, Trade.status == TradeStatus.CLOSED, Trade.closed_at >= cutoff)
        .group_by(Trade.symbol)
        .all()
    )
    result = {}
    for r in rows:
        total = r.total or 0
        wins = r.wins or 0
        result[r.symbol] = {
            "total_trades": total,
            "win_rate": wins / total if total > 0 else 0.0,
            "avg_pnl": float(r.avg_pnl) if r.avg_pnl is not None else 0.0,
        }
    return result


def _kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Kelly criterion: f* = p - q/b where b = avg_win/avg_loss."""
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    b = avg_win / avg_loss
    kelly = win_rate - (1 - win_rate) / b
    return max(0.0, min(kelly, 0.25))  # cap at 25% for safety


def _kelly_per_account(db: Session, account_id: int, days: int = 30) -> float:
    cutoff = utcnow() - timedelta(days=days)
    trades = (
        db.query(Trade.pnl)
        .filter(Trade.account_id == account_id, Trade.status == TradeStatus.CLOSED, Trade.closed_at >= cutoff)
        .all()
    )
    if not trades:
        return 0.0
    pnls = [float(t.pnl) for t in trades if t.pnl is not None]
    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p < 0]
    if not wins or not losses:
        return 0.0
    win_rate = len(wins) / len(pnls)
    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)
    return _kelly_fraction(win_rate, avg_win, avg_loss)


def _threshold_recommendations(db: Session, account_id: int, days: int = 30) -> dict[str, Any]:
    """Analyze filter effectiveness and recommend threshold adjustments."""
    cutoff = utcnow() - timedelta(days=days)
    patterns = (
        db.query(Pattern)
        .join(Trade)
        .filter(Trade.account_id == account_id, Trade.closed_at >= cutoff)
        .all()
    )
    if not patterns:
        return {"min_score": 5, "filter_adjustments": {}}

    # Group by filter snapshot keys
    filter_stats: dict[str, dict] = {}
    for p in patterns:
        features = p.features or {}
        for key, val in features.items():
            if isinstance(val, bool):
                if key not in filter_stats:
                    filter_stats[key] = {"pass_win": 0, "pass_loss": 0, "fail_win": 0, "fail_loss": 0}
                is_win = p.is_win
                if val:
                    if is_win:
                        filter_stats[key]["pass_win"] += 1
                    else:
                        filter_stats[key]["pass_loss"] += 1
                else:
                    if is_win:
                        filter_stats[key]["fail_win"] += 1
                    else:
                        filter_stats[key]["fail_loss"] += 1

    adjustments = {}
    for key, stats in filter_stats.items():
        pass_total = stats["pass_win"] + stats["pass_loss"]
        fail_total = stats["fail_win"] + stats["fail_loss"]
        if pass_total > 0:
            pass_wr = stats["pass_win"] / pass_total
        else:
            pass_wr = 0
        if fail_total > 0:
            fail_wr = stats["fail_win"] / fail_total
        else:
            fail_wr = 0
        # If filter pass has significantly lower win rate, recommend tightening
        if pass_wr < fail_wr * 0.8 and pass_total > 5:
            adjustments[key] = {"action": "tighten", "pass_wr": pass_wr, "fail_wr": fail_wr}

    return {
        "min_score": 5,  # keep default for now
        "filter_adjustments": adjustments,
    }


def nightly_learning_job() -> dict[str, Any]:
    """Main entrypoint for 02:00 UTC Celery beat job."""
    db: Session = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        results = {}
        for acc in accounts:
            wr = _win_rate_by_symbol(db, acc.id)
            kelly = _kelly_per_account(db, acc.id)
            thresholds = _threshold_recommendations(db, acc.id)
            results[f"account_{acc.id}"] = {
                "win_rates": wr,
                "kelly_fraction": kelly,
                "threshold_recommendations": thresholds,
                "computed_at": utcnow().isoformat(),
            }
        return {"status": "ok", "accounts": results}
    finally:
        db.close()


def manual_learning_job(account_id: int) -> dict[str, Any]:
    """Run learning job for a single account (useful for testing)."""
    db: Session = SessionLocal()
    try:
        wr = _win_rate_by_symbol(db, account_id)
        kelly = _kelly_per_account(db, account_id)
        thresholds = _threshold_recommendations(db, account_id)
        return {
            "status": "ok",
            "account_id": account_id,
            "win_rates": wr,
            "kelly_fraction": kelly,
            "threshold_recommendations": thresholds,
            "computed_at": utcnow().isoformat(),
        }
    finally:
        db.close()