# models/scoring.py
# Performance scoring: compute advanced statistics from a trade history.

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_score(df: pd.DataFrame) -> dict:
    """Compute a comprehensive performance scorecard from closed trades.

    Only rows whose ``"pnl"`` column is non-null are analysed — open
    positions are automatically excluded.

    Args:
        df: DataFrame of trade records as returned by
            :func:`storage.database.load_signals`.  Must contain at
            least a ``"pnl"`` column.

    Returns:
        Dictionary with the following keys:

        * ``trades``        — total number of closed trades.
        * ``winrate``       — fraction of winning trades (0–1).
        * ``total_pnl``     — cumulative PnL across all closed trades.
        * ``avg_pnl``       — average PnL per trade.
        * ``sharpe``        — annualised Sharpe ratio (assumes 252
                              trading days; ``None`` when std == 0 or
                              fewer than two trades).
        * ``max_drawdown``  — maximum peak-to-trough drawdown of the
                              equity curve.
        * ``profit_factor`` — gross profit / gross loss
                              (``float("inf")`` when there are no
                              losses).
        * ``expectancy``    — expected value per trade =
                              ``winrate × avg_win − lossrate × avg_loss``.
    """
    closed = df.dropna(subset=["pnl"]).copy()
    closed["pnl"] = pd.to_numeric(closed["pnl"], errors="coerce")
    closed = closed.dropna(subset=["pnl"])

    total = len(closed)

    if total == 0:
        return {
            "trades": 0,
            "winrate": 0.0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "sharpe": None,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
        }

    wins   = closed[closed["pnl"] > 0]
    losses = closed[closed["pnl"] < 0]
    breakeven = closed[closed["pnl"] == 0]

    win_count  = len(wins)
    loss_count = len(losses)
    # Breakeven trades are excluded from both wins and losses
    active_total = win_count + loss_count

    winrate   = win_count / active_total if active_total > 0 else 0.0
    total_pnl = float(closed["pnl"].sum())
    avg_pnl   = float(closed["pnl"].mean())

    # ── Sharpe ratio (annualised, risk-free rate = 0) ─────────────────────────
    std = float(closed["pnl"].std())
    if total >= 2 and std > 0:
        sharpe = float((avg_pnl / std) * np.sqrt(252))
    else:
        sharpe = None

    # ── Max drawdown ─────────────────────────────────────────────────────────
    equity_curve = closed["pnl"].cumsum()
    running_max  = equity_curve.cummax()
    max_drawdown = float((running_max - equity_curve).max())

    # ── Profit factor ─────────────────────────────────────────────────────────
    gross_profit = float(wins["pnl"].sum()) if not wins.empty else 0.0
    gross_loss   = abs(float(losses["pnl"].sum())) if not losses.empty else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    # ── Expectancy ────────────────────────────────────────────────────────────
    avg_win  = float(wins["pnl"].mean())  if not wins.empty   else 0.0
    avg_loss = abs(float(losses["pnl"].mean())) if not losses.empty else 0.0
    lossrate = loss_count / active_total if active_total > 0 else 0.0
    expectancy = winrate * avg_win - lossrate * avg_loss

    return {
        "trades": total,
        "winrate": winrate,
        "total_pnl": total_pnl,
        "avg_pnl": avg_pnl,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
    }
