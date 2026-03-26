# reporting/report_generator.py
# Builds a human-readable daily trading report from pipeline results.

from __future__ import annotations

import datetime
from typing import Any


def generate_daily_report(
    price: float,
    rv: float,
    iv: float,
    signal: dict[str, Any],
    event_signals: list[dict[str, Any]],
) -> str:
    """Generate a plain-text daily trading report.

    Args:
        price:         Latest close price of the underlying asset.
        rv:            Annualised realised volatility (decimal, e.g. ``0.65``).
        iv:            Annualised implied volatility (decimal, e.g. ``0.70``).
        signal:        Final trading signal dict (keys: ``signal``,
                       ``confidence``, ``reason`` / ``rationale``).
        event_signals: List of event proximity signals from
                       :func:`analytics.event_analysis.event_proximity_signal`.

    Returns:
        Multi-line string ready to be printed or stored.
    """
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    reason = signal.get("reason", signal.get("rationale", "—"))

    lines: list[str] = [
        "=" * 60,
        "  Trade Proof System — Daily Report",
        f"  {date_str}",
        "=" * 60,
        "",
        "📊 Market Snapshot",
        f"   Price        : ${price:,.2f}",
        f"   Realised Vol : {rv * 100:.1f}%",
        f"   Implied  Vol : {iv * 100:.1f}%",
        f"   IV – RV      : {(iv - rv) * 100:+.1f}%",
        "",
        "🎯 Signal",
        f"   Signal       : {signal.get('signal', '—')}",
        f"   Confidence   : {signal.get('confidence', '—')}",
        f"   Reason       : {reason}",
        "",
        "📅 Upcoming Events",
    ]

    if event_signals:
        for es in event_signals:
            lines.append(
                f"   {es['event']:20s}  J-{es['dte']}  "
                f"impact={es['impact']}  → {es['signal']}"
            )
    else:
        lines.append("   No events in the 0–7 day window.")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
