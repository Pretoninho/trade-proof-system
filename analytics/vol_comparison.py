# analytics/vol_comparison.py
# Compare realised and implied volatility to derive a directional vol edge.

from __future__ import annotations

from typing import TypedDict


class VolEdge(TypedDict):
    edge:         str    # "SELL VOL" | "BUY VOL" | "NEUTRAL"
    realized_vol: float
    implied_vol:  float
    premium:      float  # IV - RV (positive → options overpriced)


def compare_vols(realized_vol: float, implied_vol: float) -> VolEdge:
    """Compare realised volatility against implied volatility.

    Determines whether options are relatively expensive (sell vol) or cheap
    (buy vol) given the current volatility regime.

    Args:
        realized_vol: Annualised realised volatility (decimal, e.g. ``0.65``).
        implied_vol:  Annualised implied volatility (decimal, e.g. ``0.70``).

    Returns:
        :class:`VolEdge` dict with keys:

        * ``edge``         — ``"SELL VOL"``, ``"BUY VOL"``, or ``"NEUTRAL"``.
        * ``realized_vol`` — echo of the input.
        * ``implied_vol``  — echo of the input.
        * ``premium``      — IV minus RV; positive means options are overpriced.
    """
    premium = implied_vol - realized_vol

    if implied_vol > realized_vol:
        edge = "SELL VOL"   # IV > RV → options overpriced → sell volatility
    elif implied_vol < realized_vol:
        edge = "BUY VOL"    # IV < RV → options underpriced → buy volatility
    else:
        edge = "NEUTRAL"

    return VolEdge(
        edge=edge,
        realized_vol=realized_vol,
        implied_vol=implied_vol,
        premium=premium,
    )
