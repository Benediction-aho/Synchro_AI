"""Event-driven backtest engine over the intelligence stack.

No-lookahead contract: a signal computed on candles[:i] may only be executed
at candles[i+1].open. SL is evaluated before TP within a bar (conservative).
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from synchro.services.agent_engine.intelligence.candles import CandleError, to_candle_array
from synchro.services.agent_engine.intelligence.score_engine import (
    Guardrails,
    MarketContext,
    decide,
)
from synchro.services.agent_engine.intelligence.structure import (
    find_break_of_structure,
    find_fair_value_gaps,
    find_order_blocks,
)


@dataclass
class BacktestConfig:
    initial_balance: float = 1_000.0
    risk_per_trade: float = 0.01
    sl_atr_mult: float = 1.5
    tp_rr: float = 2.0
    spread_price_frac: float = 0.0002
    atr_period: int = 14
    warmup: int = 80
    structure_window: int = 120
    max_bars_in_trade: int = 500


@dataclass
class TradeRecord:
    direction: str
    entry_index: int
    entry_price: float
    exit_index: int | None
    exit_price: float | None
    sl: float
    tp: float
    pnl: float = 0.0
    outcome: str = "open"


@dataclass
class BacktestResult:
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def final_balance(self) -> float:
        return self.equity_curve[-1] if self.equity_curve else 0.0


def _atr_series(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> np.ndarray:
    tr = np.maximum(highs[1:] - lows[1:], np.maximum(
        abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1])
    ))
    tr = np.concatenate([[highs[0] - lows[0]], tr])
    out = np.empty_like(tr)
    out[0] = tr[0]
    alpha = 2.0 / (period + 1.0)
    for i in range(1, tr.size):
        out[i] = alpha * tr[i] + (1.0 - alpha) * out[i - 1]
    return out


def _build_context(candles: list[dict], window: list[dict]) -> MarketContext:
    from synchro.services.agent_engine.intelligence.momentum import momentum_confluence
    from synchro.services.agent_engine.intelligence.trend import validate_trend_block

    snapshot = momentum_confluence(window)
    alignment, _votes = validate_trend_block({"entry": window})

    hint = "BUY"
    if alignment == "bearish":
        hint = "SELL"
    elif alignment is None and snapshot.score < 0:
        hint = "SELL"
        alignment = "bearish"

    regime = "trend_up" if hint == "BUY" else "trend_down"
    if alignment is None:
        regime = "range"

    return MarketContext(
        symbol="BACKTEST",
        direction_hint=hint,
        regime=regime,
        trend_alignment=alignment,
        momentum_score=snapshot.score,
        rsi=snapshot.rsi,
        candles=window,
        order_blocks=find_order_blocks(window, lookback=2, max_blocks=8),
        fair_value_gaps=find_fair_value_gaps(window, max_gaps=8),
        bos_events=find_break_of_structure(window, swing_window=3)[-5:],
    )


def run_backtest(
    candles: list[dict[str, Any]],
    config: BacktestConfig | None = None,
    guardrails: Guardrails | None = None,
) -> BacktestResult:
    cfg = config or BacktestConfig()
    guards = guardrails or Guardrails()
    if cfg.risk_per_trade <= 0 or cfg.risk_per_trade > 0.05:
        raise CandleError("risk_per_trade must be in (0, 0.05]")
    min_warmup = 50 + min(50, 100) + 10
    if cfg.warmup < min_warmup:
        cfg.warmup = min_warmup
    arr = to_candle_array(candles, min_length=cfg.warmup + 10)
    n = len(arr)
    atr = _atr_series(arr[:, 2], arr[:, 3], arr[:, 4], cfg.atr_period)

    result = BacktestResult()
    balance = cfg.initial_balance
    result.equity_curve.append(balance)
    open_trade: TradeRecord | None = None
    pending_signal: str | None = None

    for i in range(cfg.warmup, n):
        if open_trade is None and pending_signal is not None and i + 1 <= n - 1:
            pass

        if open_trade is not None:
            bar_high, bar_low, close_i = arr[i, 2], arr[i, 3], arr[i, 4]
            hit_sl = (
                bar_low <= open_trade.sl
                if open_trade.direction == "BUY"
                else bar_high >= open_trade.sl
            )
            hit_tp = (
                bar_high >= open_trade.tp
                if open_trade.direction == "BUY"
                else bar_low <= open_trade.tp
            )
            bars_held = i - open_trade.entry_index
            timeout = bars_held >= cfg.max_bars_in_trade

            if hit_sl or hit_tp or timeout:
                if hit_sl:
                    exit_price = open_trade.sl
                    outcome = "loss"
                elif hit_tp:
                    exit_price = open_trade.tp
                    outcome = "win"
                else:
                    exit_price = float(close_i)
                    outcome = "timeout"
                risk_amount = balance * cfg.risk_per_trade
                per_unit = abs(open_trade.entry_price - open_trade.sl)
                units = risk_amount / per_unit if per_unit > 0 else 0.0
                move = (
                    exit_price - open_trade.entry_price
                    if open_trade.direction == "BUY"
                    else open_trade.entry_price - exit_price
                )
                spread_cost = cfg.spread_price_frac * open_trade.entry_price
                pnl = move * units - spread_cost * units
                balance += pnl
                open_trade.exit_index = i
                open_trade.exit_price = exit_price
                open_trade.pnl = round(pnl, 6)
                open_trade.outcome = outcome
                result.trades.append(open_trade)
                result.equity_curve.append(round(balance, 6))
                open_trade = None
                continue

        if open_trade is not None:
            continue

        if i + 1 >= n:
            break
        window = candles[max(0, i + 1 - cfg.structure_window) : i + 1]
        context = _build_context(candles[: i + 1], window)
        decision = decide(context, guards)

        if decision.decision in ("BUY", "SELL") and decision.score == 5:
            entry_price = float(arr[i + 1, 1])
            if decision.decision == "BUY":
                entry_price *= 1.0 + cfg.spread_price_frac
            else:
                entry_price *= 1.0 - cfg.spread_price_frac
            stop_distance = atr[i] * cfg.sl_atr_mult
            if stop_distance <= 0:
                continue
            if decision.decision == "BUY":
                sl = entry_price - stop_distance
                tp = entry_price + stop_distance * cfg.tp_rr
            else:
                sl = entry_price + stop_distance
                tp = entry_price - stop_distance * cfg.tp_rr
            open_trade = TradeRecord(decision.decision, i + 1, entry_price, None, None, sl, tp)
            pending_signal = None

    if open_trade is not None:
        last_close = float(arr[-1, 4])
        risk_amount = balance * cfg.risk_per_trade
        per_unit = abs(open_trade.entry_price - open_trade.sl)
        units = risk_amount / per_unit if per_unit > 0 else 0.0
        move = (
            last_close - open_trade.entry_price
            if open_trade.direction == "BUY"
            else open_trade.entry_price - last_close
        )
        pnl = move * units
        balance += pnl
        open_trade.exit_index = n - 1
        open_trade.exit_price = last_close
        open_trade.pnl = round(pnl, 6)
        open_trade.outcome = "eod"
        result.trades.append(open_trade)
        result.equity_curve.append(round(balance, 6))

    result.metrics = compute_metrics(result, cfg.initial_balance)
    return result


def compute_metrics(result: BacktestResult, initial_balance: float) -> dict[str, float]:
    closed = [t for t in result.trades if t.outcome != "open"]
    if not closed:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "sharpe_per_trade": 0.0,
            "final_balance": float(initial_balance),
            "return_pct": 0.0,
        }
    pnls = [t.pnl for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    equity = np.array(result.equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdowns = (peak - equity) / peak
    max_dd = float(drawdowns.max()) if drawdowns.size else 0.0

    returns = np.array(pnls, dtype=float)
    std = float(returns.std())
    sharpe = float(returns.mean() / std) if std > 0 else 0.0
    final = result.equity_curve[-1]

    return {
        "total_trades": len(closed),
        "win_rate": round(len(wins) / len(closed), 4),
        "profit_factor": round(gross_win / gross_loss, 4) if gross_loss > 0 else float("inf"),
        "max_drawdown": round(max_dd, 4),
        "sharpe_per_trade": round(sharpe, 4),
        "final_balance": round(final, 2),
        "return_pct": round((final / initial_balance - 1.0) * 100, 3),
    }
