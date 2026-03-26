# analytics/signals.py
# Trading signal generation based on volatility regime and price action.

from __future__ import annotations

from typing import TypedDict

import pandas as pd


# ── Volatility / signal thresholds ────────────────────────────────────────────
ELEVATED_DVOL_THRESHOLD = 80     # DVOL level above which vol is considered expensive


def vol_signal(realized_vol: float, implied_vol: float) -> str:
    """Generate a volatility trading signal.

    Compares realised (historical) volatility against implied volatility to
    identify whether options are relatively expensive or cheap.

    Args:
        realized_vol: Annualised realised volatility (decimal).
        implied_vol:  Annualised implied volatility (decimal).

    Returns:
        One of ``"SELL VOL"``, ``"BUY VOL"``, or ``"NEUTRAL"``.
    """
    if implied_vol > realized_vol:
        return "SELL VOL"   # IV premium → options overpriced → sell volatility
    elif implied_vol < realized_vol:
        return "BUY VOL"    # IV discount → options underpriced → buy volatility
    else:
        return "NEUTRAL"


def trend_signal(df: "pd.DataFrame", fast: int = 20, slow: int = 50) -> str:
    """Simple moving-average crossover trend signal.

    Args:
        df:   OHLCV DataFrame with a ``"close"`` column.
        fast: Short SMA window in candles.
        slow: Long SMA window in candles.

    Returns:
        ``"BULLISH"``, ``"BEARISH"``, or ``"NEUTRAL"``.
    """
    close = df["close"]
    sma_fast = close.rolling(fast).mean().iloc[-1]
    sma_slow = close.rolling(slow).mean().iloc[-1]

    if sma_fast > sma_slow:
        return "BULLISH"
    elif sma_fast < sma_slow:
        return "BEARISH"
    else:
        return "NEUTRAL"


class VolCrushSignal(TypedDict):
    signal:     str
    strategy:   str
    confidence: str
    rationale:  str


def vol_crush_signal(is_crush: bool, dvol: float) -> VolCrushSignal:
    """Translate a vol-crush detection into an actionable trading decision.

    Decision tree:

    1. **Vol crush confirmed** → sell premium immediately (regime shifted, IV
       collapsing, theta decay accelerates).
    2. **DVOL elevated (> 80) but no confirmed crush** → watch for the crush;
       conditions are ripe for a short-premium setup.
    3. **Otherwise** → no statistical edge; stand aside.

    Args:
        is_crush: Output of :func:`analytics.vol_crush.detect_vol_crush`.
        dvol:     Current DVOL level (annualised %).

    Returns:
        Dictionary with keys ``signal``, ``strategy``, ``confidence``, and
        ``rationale``.
    """
    if is_crush:
        return VolCrushSignal(
            signal="SELL PREMIUM",
            strategy="Short straddle / Short strangle",
            confidence="HIGH",
            rationale="Vol crush confirmed — IV collapsing after event resolution. "
                      "Short premium at-the-money to harvest vega + theta.",
        )

    if dvol > ELEVATED_DVOL_THRESHOLD:
        return VolCrushSignal(
            signal="WAIT / SELL HIGH VOL",
            strategy="Short strangle (wide strikes)",
            confidence="MEDIUM",
            rationale=f"DVOL elevated at {dvol:.1f} but no confirmed crush yet. "
                      "Wait for the event catalyst; sell into the vol spike.",
        )

    return VolCrushSignal(
        signal="NO EDGE",
        strategy="-",
        confidence="LOW",
        rationale=f"DVOL at {dvol:.1f} — no vol crush and no elevated regime. "
                  "Stand aside or look for long-vol setups.",
    )
