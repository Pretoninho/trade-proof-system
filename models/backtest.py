# models/backtest.py
# Backtest engine: tests SELL VOL vs BUY VOL edge on historical price data.
#
# The simulation is intentionally simplified (no real option pricing):
#   - Each bar a signal is computed from RV vs IV.
#   - A +1 / -1 PnL is recorded depending on whether the outcome matched the signal.
#   - performance_metrics() summarises the resulting equity curve.

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.volatility import realized_volatility
from analytics.vol_comparison import compare_vols

# Minimum lookback required to compute a stable realised-vol estimate.
_MIN_LOOKBACK = 50


def backtest_vol_strategy(
    df: pd.DataFrame,
    dvol_series: "list[float] | pd.Series",
) -> pd.Series:
    """Backtest a simple SELL VOL / BUY VOL strategy on historical data.

    For each bar *i* (starting after ``_MIN_LOOKBACK`` candles):

    1. Compute realised volatility over the preceding 50 candles.
    2. Read implied volatility from *dvol_series[i]* (annualised %, converted
       to decimal internally).
    3. Derive the edge signal via :func:`analytics.vol_comparison.compare_vols`.
    4. Compare the next bar's actual price move against the IV-implied daily
       expected move (``IV / √365``).  Record ``+1`` (win) or ``-1`` (loss).

    Args:
        df:          OHLCV DataFrame with a ``"close"`` column, sorted oldest
                     first.
        dvol_series: Sequence of implied-volatility values (annualised **%**,
                     e.g. 70 for 70 %) aligned to *df*'s index.  A constant
                     list is acceptable for quick exploration (the dashboard
                     builds one from the live DVOL snapshot).

    Returns:
        :class:`pandas.Series` of per-bar PnL values (``+1`` / ``-1`` / ``0``).
        Length is ``len(df) - _MIN_LOOKBACK - 1``.
    """
    results: list[int] = []

    for i in range(_MIN_LOOKBACK, len(df) - 1):
        lookback_window = df.iloc[i - _MIN_LOOKBACK: i]

        price_today = float(df["close"].iloc[i])
        price_next  = float(df["close"].iloc[i + 1])

        realized_vol = realized_volatility(lookback_window)
        # dvol_series values are in annualised % → convert to decimal
        implied_vol  = float(dvol_series[i]) / 100.0

        signal = compare_vols(realized_vol, implied_vol)

        # Daily expected move implied by IV as a % of spot (1-σ, log-normal).
        # Both sides are percentage moves, so the comparison is consistent.
        expected_daily_move = implied_vol / np.sqrt(365)
        actual_move = abs(price_next - price_today) / price_today

        pnl: int = 0
        if signal["edge"] == "SELL VOL":
            # Win if the market moved less than the IV-implied move
            pnl = 1 if actual_move < expected_daily_move else -1
        elif signal["edge"] == "BUY VOL":
            # Win if the market moved more than the IV-implied move
            pnl = 1 if actual_move > expected_daily_move else -1
        # NEUTRAL → pnl stays 0 (no trade)

        results.append(pnl)

    return pd.Series(results, dtype=int)


def performance_metrics(pnl_series: pd.Series) -> dict:
    """Compute key performance statistics from a backtest PnL series.

    Args:
        pnl_series: Series of per-bar PnL values as returned by
                    :func:`backtest_vol_strategy`.

    Returns:
        Dictionary with the following keys:

        * ``trades``       — total number of bars with a non-zero signal.
        * ``winrate``      — fraction of winning trades (0–1).
        * ``pnl_total``    — sum of all PnL values.
        * ``max_drawdown`` — maximum peak-to-trough drawdown of the equity curve.
    """
    active = pnl_series[pnl_series != 0]
    total_trades = len(active)

    wins   = int((active > 0).sum())
    winrate = wins / total_trades if total_trades > 0 else 0.0

    equity_curve   = pnl_series.cumsum()
    running_max    = equity_curve.cummax()
    max_drawdown   = float((running_max - equity_curve).max())

    return {
        "trades":       total_trades,
        "winrate":      winrate,
        "pnl_total":    pnl_series.sum(),
        "max_drawdown": max_drawdown,
    }
