# models/tracking.py
# Trade-record helpers: create new signal entries and close open positions.
# Also provides TradeTracker — a lightweight in-memory trade log with built-in
# performance statistics (trades, win rate, cumulative PnL, drawdown, per-signal).

from __future__ import annotations

import datetime

import pandas as pd

from models.pnl import _active_count


class TradeTracker:
    """In-memory trade journal with live performance statistics.

    Usage::

        tracker = TradeTracker()
        tracker.log_trade("SELL VOL", entry=30_000, exit_price=29_500, pnl=500)
        tracker.log_trade("BUY VOL",  entry=29_500, exit_price=29_000, pnl=-500)

        df      = tracker.to_dataframe()
        summary = tracker.summary()
        by_sig  = tracker.performance_by_signal()
    """

    def __init__(self) -> None:
        self.trades: list[dict] = []

    # ── Recording ──────────────────────────────────────────────────────────────

    def log_trade(
        self,
        signal: str,
        entry: float,
        exit_price: float,
        pnl: float,
    ) -> None:
        """Append a closed trade to the journal.

        Args:
            signal:     Signal label that triggered the trade
                        (e.g. ``"SELL VOL"``, ``"BUY VOL"``).
            entry:      Entry price of the underlying asset.
            exit_price: Exit price of the underlying asset.
            pnl:        Realised profit / loss for this trade.
        """
        self.trades.append(
            {
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "signal":    signal,
                "entry":     entry,
                "exit":      exit_price,
                "pnl":       pnl,
            }
        )

    # ── Export ─────────────────────────────────────────────────────────────────

    def to_dataframe(self) -> pd.DataFrame:
        """Return all logged trades as a :class:`pandas.DataFrame`.

        Returns an empty DataFrame (with the correct columns) when no
        trades have been logged yet.
        """
        if not self.trades:
            return pd.DataFrame(columns=["timestamp", "signal", "entry", "exit", "pnl"])
        return pd.DataFrame(self.trades)

    # ── Statistics ─────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Compute aggregate performance statistics across all logged trades.

        Returns:
            Dictionary with the following keys:

            * ``trades``       — total number of logged trades.
            * ``winrate``      — fraction of winning trades (0–1).
            * ``pnl_total``    — sum of all PnL values.
            * ``pnl_avg``      — average PnL per trade.
            * ``max_drawdown`` — maximum peak-to-trough drawdown of the
                                 cumulative PnL curve.
        """
        df = self.to_dataframe()

        if df.empty:
            return {
                "trades":       0,
                "winrate":      0.0,
                "pnl_total":    0.0,
                "pnl_avg":      0.0,
                "max_drawdown": 0.0,
            }

        total        = len(df)
        wins         = int((df["pnl"] > 0).sum())
        active       = _active_count(df["pnl"])
        winrate      = wins / active if active > 0 else 0.0
        pnl_total    = float(df["pnl"].sum())
        pnl_avg      = float(df["pnl"].mean())

        equity       = df["pnl"].cumsum()
        running_max  = equity.cummax()
        max_drawdown = float((running_max - equity).max())

        return {
            "trades":       total,
            "winrate":      winrate,
            "pnl_total":    pnl_total,
            "pnl_avg":      pnl_avg,
            "max_drawdown": max_drawdown,
        }

    def performance_by_signal(self) -> pd.DataFrame:
        """Break down performance statistics by signal type.

        Returns:
            DataFrame indexed by ``signal`` with columns:
            ``trades``, ``winrate``, ``pnl_total``, ``pnl_avg``.
            Returns an empty DataFrame when no trades have been logged.
        """
        df = self.to_dataframe()

        if df.empty:
            return pd.DataFrame(
                columns=["signal", "trades", "winrate", "pnl_total", "pnl_avg"]
            ).set_index("signal")

        rows = []
        for sig, group in df.groupby("signal"):
            total   = len(group)
            active  = _active_count(group["pnl"])
            wins    = int((group["pnl"] > 0).sum())
            winrate = wins / active if active > 0 else 0.0
            rows.append(
                {
                    "signal":    sig,
                    "trades":    total,
                    "winrate":   winrate,
                    "pnl_total": float(group["pnl"].sum()),
                    "pnl_avg":   float(group["pnl"].mean()),
                }
            )

        return pd.DataFrame(rows).set_index("signal")


def create_signal_record(
    price: float,
    signal: str,
    strategy: str,
) -> dict:
    """Build a new, open trade record ready to be persisted.

    Args:
        price:    Entry price of the underlying asset.
        signal:   Signal label (e.g. ``"SELL VOL"``, ``"BUY VOL"``).
        strategy: Strategy identifier (e.g. ``"vol_crush"``, ``"event"``).

    Returns:
        Dictionary with the following keys:

        * ``date``        — UTC timestamp at record creation.
        * ``price_entry`` — Entry price supplied by the caller.
        * ``signal``      — Signal label.
        * ``strategy``    — Strategy identifier.
        * ``price_exit``  — ``None`` until the trade is closed.
        * ``pnl``         — ``None`` until the trade is closed.
    """
    return {
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "price_entry": price,
        "signal": signal,
        "strategy": strategy,
        "price_exit": None,
        "pnl": None,
    }


def update_trade(
    df: pd.DataFrame,
    index: int,
    exit_price: float,
    pnl: float,
) -> pd.DataFrame:
    """Close an open trade by filling its exit price and PnL.

    The function mutates *df* in place **and** returns it so callers can
    chain the call (e.g. ``df = update_trade(df, i, exit, pnl)``).

    Args:
        df:         DataFrame of signals as returned by
                    :func:`storage.database.load_signals`.
        index:      Integer position of the row to update (iloc-style).
        exit_price: Closing price of the underlying asset.
        pnl:        Realised profit/loss for this trade.

    Returns:
        The updated DataFrame.
    """
    df.loc[index, "price_exit"] = exit_price
    df.loc[index, "pnl"] = pnl

    return df
