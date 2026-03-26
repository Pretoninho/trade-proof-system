# models/pnl.py
# PnL computation utilities: calculate realised profit/loss from trade records
# and build cumulative PnL series for further analysis.

from __future__ import annotations

import pandas as pd


def _active_count(pnl_col: "pd.Series") -> int:
    """Return the number of non-zero (win or loss) entries in *pnl_col*."""
    return int(((pnl_col > 0) | (pnl_col < 0)).sum())


def compute_pnl(signal: str, entry: float, exit_price: float) -> float:
    """Compute the raw PnL for a single trade given its direction.

    Convention:
    * ``"SELL VOL"`` / ``"SELL PREMIUM"`` — short position → profit when price
      falls (entry − exit).
    * All other signals (``"BUY VOL"``, ``"BUY"``, …) — long position → profit
      when price rises (exit − entry).

    Args:
        signal:     Signal label used to determine trade direction.
        entry:      Entry price of the underlying asset.
        exit_price: Exit price of the underlying asset.

    Returns:
        Signed PnL value (positive = profit, negative = loss).
    """
    if "SELL" in signal.upper():
        return entry - exit_price
    return exit_price - entry


def cumulative_pnl(pnl_series: pd.Series) -> pd.Series:
    """Build a cumulative PnL equity curve from a series of per-trade PnL values.

    Args:
        pnl_series: :class:`pandas.Series` of per-trade PnL values.

    Returns:
        :class:`pandas.Series` of the same length representing the running
        cumulative sum (equity curve).
    """
    return pnl_series.cumsum()


def pnl_by_signal(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate PnL statistics grouped by signal type.

    The input DataFrame must have at least a ``"signal"`` column and a
    numeric ``"pnl"`` column.  Open trades (``pnl`` is ``NaN``) are
    silently excluded.

    Args:
        df: DataFrame of trade records — typically the output of
            :func:`storage.database.load_signals` or
            :meth:`models.tracking.TradeTracker.to_dataframe`.

    Returns:
        DataFrame indexed by ``signal`` with columns:

        * ``trades``    — number of closed trades for that signal.
        * ``winrate``   — fraction of winning trades (0–1).
        * ``pnl_total`` — cumulative PnL.
        * ``pnl_avg``   — average PnL per trade.

        Returns an empty DataFrame with those columns when *df* is empty
        or has no closed trades.
    """
    empty = pd.DataFrame(
        columns=["signal", "trades", "winrate", "pnl_total", "pnl_avg"]
    ).set_index("signal")

    if df.empty or "pnl" not in df.columns or "signal" not in df.columns:
        return empty

    closed = df.dropna(subset=["pnl"])
    closed = closed.assign(pnl=pd.to_numeric(closed["pnl"], errors="coerce"))
    closed = closed.dropna(subset=["pnl"])

    if closed.empty:
        return empty

    rows = []
    for sig, group in closed.groupby("signal"):
        active  = _active_count(group["pnl"])
        wins    = int((group["pnl"] > 0).sum())
        winrate = wins / active if active > 0 else 0.0
        rows.append(
            {
                "signal":    sig,
                "trades":    len(group),
                "winrate":   winrate,
                "pnl_total": float(group["pnl"].sum()),
                "pnl_avg":   float(group["pnl"].mean()),
            }
        )

    return pd.DataFrame(rows).set_index("signal")
