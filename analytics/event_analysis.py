# analytics/event_analysis.py
# Converts a list of upcoming events into actionable proximity signals.
#
# Timing zones:
#   0 – 2 days  →  POST EVENT  (vol crush window, sell premium)
#   3 – 7 days  →  PRE  EVENT  (vol build-up window, buy vol / wait)

from __future__ import annotations

import datetime
from typing import TypedDict

from data.events_data import Event


class EventSignal(TypedDict):
    event:  str
    dte:    int
    impact: str
    signal: str


def days_to_event(event_date: datetime.datetime) -> int:
    """Return the number of whole days until *event_date* from today (UTC).

    Args:
        event_date: Scheduled event datetime (UTC).

    Returns:
        Integer day count.  Negative values mean the event is in the past.
    """
    today = datetime.datetime.utcnow()
    return (event_date - today).days


def event_proximity_signal(events: list[Event]) -> list[EventSignal]:
    """Classify each upcoming event by its distance from today.

    Decision zones (days-to-event = DTE):

    * ``0 ≤ DTE ≤ 2``  → **POST EVENT** → volatility crush setup.
      Uncertainty resolved; IV collapsing → sell premium.
    * ``3 ≤ DTE ≤ 7``  → **PRE EVENT** → vol build-up window.
      Market prices in the move → buy vol or wait for the crush.

    Events beyond 7 days or already passed by more than 2 days are omitted
    (no immediate actionable edge).

    Args:
        events: List of :class:`~data.events_data.Event` dicts.

    Returns:
        List of :class:`EventSignal` dicts, one per relevant event.
    """
    signals: list[EventSignal] = []

    for event in events:
        dte = days_to_event(event["date"])

        if 0 <= dte <= 2:
            signals.append(
                EventSignal(
                    event=event["name"],
                    dte=dte,
                    impact=event["impact"],
                    signal="POST EVENT → VOL CRUSH SETUP",
                )
            )

        elif 3 <= dte <= 7:
            signals.append(
                EventSignal(
                    event=event["name"],
                    dte=dte,
                    impact=event["impact"],
                    signal="PRE EVENT → BUY VOL / WAIT",
                )
            )

    return signals
