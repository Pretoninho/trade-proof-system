# analytics/volatility.py
# Volatility metrics used as the core analytical edge of the system.

import numpy as np
import pandas as pd

from config.settings import ANNUALISATION_FACTOR


def realized_volatility(df: pd.DataFrame, window: int | None = None) -> float:
    """Compute the annualised realised (historical) volatility.

    Uses log returns so the metric is scale-independent and additive.

    Args:
        df:     OHLCV DataFrame with a ``"close"`` column.
        window: Optional rolling window (number of candles).  When *None*
                the entire series is used.

    Returns:
        Annualised volatility as a decimal (e.g. ``0.65`` = 65 %).
    """
    closes = df["close"]
    if window is not None:
        closes = closes.iloc[-window:]

    returns = np.log(closes / closes.shift(1)).dropna()
    vol = returns.std() * np.sqrt(ANNUALISATION_FACTOR)
    return float(vol)


def expected_move(vol: float, price: float, horizon_days: float = 1) -> float:
    """Compute the expected 1-σ price move over *horizon_days*.

    Derived from the log-normal assumption:
        EM = S × σ × √(T / 365)

    Args:
        vol:           Annualised volatility (decimal, e.g. ``0.65``).
        price:         Current spot price.
        horizon_days:  Time horizon in calendar days.

    Returns:
        Expected 1-σ move in price units (same currency as *price*).
    """
    return price * vol * np.sqrt(horizon_days / 365)


def rolling_realized_volatility(df: pd.DataFrame, window: int = 24) -> pd.Series:
    """Return a rolling annualised realised volatility series.

    Useful for plotting how volatility evolves over time.

    Args:
        df:     OHLCV DataFrame with a ``"close"`` column.
        window: Rolling window size in candles (default: 24 for 24-hour RV
                when using 1 h candles).

    Returns:
        pandas Series of annualised volatility values.
    """
    returns = np.log(df["close"] / df["close"].shift(1))
    return returns.rolling(window).std() * np.sqrt(ANNUALISATION_FACTOR)
