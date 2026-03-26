# data/events_data.py
# Macro & crypto event calendar.
#
# Returns a list of upcoming scheduled events that may trigger volatility moves.
# Currently backed by a static mock — swap ``get_upcoming_events`` for a live
# API call (e.g. Investing.com economic calendar, CoinMarketCal) in production.

from __future__ import annotations

import datetime
from typing import TypedDict


class Event(TypedDict):
    name:   str
    date:   datetime.datetime
    impact: str   # "HIGH" | "MEDIUM" | "LOW"


def get_upcoming_events() -> list[Event]:
    """Return a list of upcoming macro & crypto events.

    Each entry contains:

    * ``name``   — human-readable event label.
    * ``date``   — scheduled event datetime (UTC).
    * ``impact`` — expected volatility impact: ``"HIGH"``, ``"MEDIUM"``,
      or ``"LOW"``.

    Returns:
        List of :class:`Event` dicts ordered by date (closest first).
    """
    today = datetime.datetime.utcnow()

    # Build relative dates so the mock data stays relevant regardless of when
    # the system is run.  Replace with real API data for production use.
    return sorted(
        [
            Event(
                name="FOMC",
                date=today + datetime.timedelta(days=20),
                impact="HIGH",
            ),
            Event(
                name="CPI",
                date=today + datetime.timedelta(days=15),
                impact="HIGH",
            ),
            Event(
                name="BTC Options Expiry",
                date=today + datetime.timedelta(days=5),
                impact="MEDIUM",
            ),
            Event(
                name="ETH Unlock",
                date=today + datetime.timedelta(days=1),
                impact="MEDIUM",
            ),
        ],
        key=lambda e: e["date"],
    )
