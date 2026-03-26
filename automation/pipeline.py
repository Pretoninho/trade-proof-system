# automation/pipeline.py
# Full analysis pipeline — collects data, generates signals, persists the
# result, and produces a ready-to-publish daily report.
#
# Call ``run_pipeline()`` to execute one complete cycle.

from __future__ import annotations

from config.settings import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, DEFAULT_LIMIT, DERIBIT_CURRENCY
from data.market_data import get_ohlcv
from data.options_data import get_dvol
from data.events_data import get_upcoming_events

from analytics.volatility import realized_volatility
from analytics.vol_comparison import compare_vols
from analytics.event_analysis import event_proximity_signal
from analytics.signals import event_driven_signal

from models.tracking import create_signal_record
from storage.database import save_signal

from reporting.report_generator import generate_daily_report


def run_pipeline(
    symbol: str = DEFAULT_SYMBOL,
    timeframe: str = DEFAULT_TIMEFRAME,
    limit: int = DEFAULT_LIMIT,
    dvol_currency: str = DERIBIT_CURRENCY,
) -> dict:
    """Execute a full analysis cycle without any manual intervention.

    Steps:
        1. Fetch OHLCV market data.
        2. Compute realised and implied volatility.
        3. Derive the vol edge (RV vs IV comparison).
        4. Collect upcoming macro/crypto events and build event signals.
        5. Combine vol edge and event signals into a single final signal.
        6. Persist the signal record to storage.
        7. Generate a plain-text daily report.

    Args:
        symbol:        Trading pair (default from settings).
        timeframe:     Candle interval (default from settings).
        limit:         Number of OHLCV candles to fetch (default from settings).
        dvol_currency: Deribit DVOL currency — ``"BTC"`` or ``"ETH"``.

    Returns:
        Dictionary with keys:

        * ``price``   — latest close price.
        * ``rv``      — annualised realised volatility (decimal).
        * ``iv``      — annualised implied volatility (decimal).
        * ``signal``  — final signal dict.
        * ``report``  — formatted daily report string.
    """
    # ── 1. Market data ────────────────────────────────────────────────────────
    df = get_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
    price = float(df["close"].iloc[-1])

    # ── 2. Volatility ─────────────────────────────────────────────────────────
    rv = realized_volatility(df)
    iv = get_dvol(dvol_currency) / 100   # DVOL is expressed in %; convert to decimal

    # ── 3. Vol edge ───────────────────────────────────────────────────────────
    vol_edge = compare_vols(rv, iv)
    base_signal: dict = {
        "signal":     vol_edge["edge"],
        "confidence": "MEDIUM",
        "reason":     "RV vs IV comparison",
    }

    # ── 4. Events ─────────────────────────────────────────────────────────────
    events = get_upcoming_events()
    event_signals = event_proximity_signal(events)

    # ── 5. Final signal ───────────────────────────────────────────────────────
    final_signal: dict = event_driven_signal(base_signal, event_signals)

    # ── 6. Persist ────────────────────────────────────────────────────────────
    record = create_signal_record(
        price,
        final_signal.get("signal", ""),
        final_signal.get("strategy", "pipeline"),
    )
    save_signal(record)

    # ── 7. Report ─────────────────────────────────────────────────────────────
    report = generate_daily_report(price, rv, iv, final_signal, event_signals)

    return {
        "price":  price,
        "rv":     rv,
        "iv":     iv,
        "signal": final_signal,
        "report": report,
    }
