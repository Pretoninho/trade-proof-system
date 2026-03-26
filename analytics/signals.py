# analytics/signals.py
# Trading signal generation based on volatility regime and price action.

from __future__ import annotations

import pandas as pd


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
