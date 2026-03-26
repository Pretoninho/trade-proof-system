# models/tracking.py
# Trade-record helpers: create new signal entries and close open positions.

from __future__ import annotations

import datetime

import pandas as pd


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
