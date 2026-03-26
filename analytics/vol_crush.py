# analytics/vol_crush.py
# Vol-crush detection: identifies sharp implied-volatility collapses that
# signal a regime shift from high-fear to low-fear environments.
#
# A "vol crush" occurs when implied volatility (DVOL) drops rapidly after a
# headline event (FOMC, CPI, earnings, etc.) is resolved.  The premium that
# was priced in for the event evaporates, creating attractive short-premium
# opportunities (short straddle / short strangle).

from __future__ import annotations

import pandas as pd


def detect_vol_crush(
    dvol_series: "list[float] | pd.Series",
    threshold_drop: float = 0.10,
) -> bool:
    """Detect a sharp volatility collapse between the two most-recent readings.

    A vol crush is flagged when the relative drop from the previous DVOL
    reading to the latest one exceeds *threshold_drop*.

    Args:
        dvol_series:     An ordered sequence of DVOL values (oldest → newest).
                         At least 2 elements are required.
        threshold_drop:  Minimum relative drop to qualify as a crush
                         (default: 0.10 = 10 %).

    Returns:
        ``True`` if a vol crush is detected, ``False`` otherwise.
    """
    if len(dvol_series) < 2:
        return False

    prev   = float(dvol_series[-2])
    latest = float(dvol_series[-1])

    if prev <= 0:
        return False

    drop = (prev - latest) / prev
    return drop > threshold_drop


def vol_crush_metrics(dvol_df: pd.DataFrame) -> dict:
    """Compute a set of vol-crush diagnostic metrics from a DVOL history.

    Analyses the ``close`` column of a DVOL DataFrame (as returned by
    :func:`data.options_data.get_dvol_history`) and returns a concise summary
    useful for dashboard display and decision-making.

    Metrics computed:

    * ``current``    — latest DVOL value.
    * ``avg_30d``    — rolling 30-period mean of DVOL (regime reference).
    * ``pct_from_avg`` — how far the current DVOL sits from its 30-period mean
                         (positive = above average → expensive vol).
    * ``drop_1d``    — 1-period relative change (negative = vol dropping).
    * ``drop_7d``    — 7-period relative change.
    * ``is_elevated`` — ``True`` when current DVOL > 30-period mean.
    * ``crush_detected`` — ``True`` when the latest 1-period drop > 10 %.

    Args:
        dvol_df: DataFrame with at least a ``close`` column, sorted oldest
                 first (as returned by ``get_dvol_history``).

    Returns:
        Dictionary of metrics.
    """
    closes = dvol_df["close"].dropna()

    current   = float(closes.iloc[-1])
    avg_30d   = float(closes.tail(30).mean())
    pct_from_avg = (current - avg_30d) / avg_30d if avg_30d else 0.0

    drop_1d = float((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) if len(closes) >= 2 and closes.iloc[-2] != 0 else 0.0
    drop_7d = float((closes.iloc[-1] - closes.iloc[-7]) / closes.iloc[-7]) if len(closes) >= 7 and closes.iloc[-7] != 0 else 0.0

    return {
        "current":       current,
        "avg_30d":       avg_30d,
        "pct_from_avg":  pct_from_avg,
        "drop_1d":       drop_1d,
        "drop_7d":       drop_7d,
        "is_elevated":   current > avg_30d,
        "crush_detected": detect_vol_crush(closes.tolist()),
    }
