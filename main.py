#!/usr/bin/env python3
# main.py
# Orchestrator — runs a full analytical cycle from the command line.
#
# Usage:
#   python main.py
#   python main.py --symbol ETH/USDT --timeframe 4h

import argparse

from config.settings import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, DEFAULT_LIMIT, DERIBIT_CURRENCY
from data.market_data import get_ohlcv
from data.options_data import get_dvol_history
from analytics.volatility import realized_volatility, expected_move
from analytics.signals import vol_signal, trend_signal, vol_crush_signal, event_driven_signal
from analytics.vol_crush import vol_crush_metrics
from analytics.event_analysis import event_proximity_signal
from data.events_data import get_upcoming_events
from models.probability import probability_move, probability_range


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trade Proof System — CLI orchestrator")
    parser.add_argument("--symbol",    default=DEFAULT_SYMBOL,    help="Trading pair (default: BTC/USDT)")
    parser.add_argument("--timeframe", default=DEFAULT_TIMEFRAME, help="Candle timeframe (default: 1h)")
    parser.add_argument("--limit",     default=DEFAULT_LIMIT, type=int, help="Number of candles")
    parser.add_argument("--iv",        default=None, type=float,
                        help="Implied volatility in %% (e.g. 70 for 70%%). "
                             "If omitted the script uses realised vol as a proxy.")
    parser.add_argument("--horizon",   default=1, type=float, help="Horizon in days (default: 1)")
    parser.add_argument("--dvol-currency", default=DERIBIT_CURRENCY,
                        help="DVOL currency to fetch from Deribit (BTC or ETH, default: BTC)")
    parser.add_argument("--dvol-days", default=30, type=int,
                        help="Days of DVOL history to analyse (default: 30)")
    # ── Autonomous mode ───────────────────────────────────────────────────────
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run the pipeline autonomously on a fixed interval (see --interval).",
    )
    parser.add_argument(
        "--interval",
        default=24.0,
        type=float,
        help="Scheduler interval in hours when --schedule is used (default: 24).",
    )
    return parser.parse_args()


def run(symbol: str, timeframe: str, limit: int, iv_pct: float | None, horizon: float,
        dvol_currency: str = DERIBIT_CURRENCY, dvol_days: int = 30) -> None:
    print(f"\n{'=' * 60}")
    print(f"  Trade Proof System — {symbol} | {timeframe} | last {limit} candles")
    print(f"{'=' * 60}\n")

    # ── 1. Fetch data ─────────────────────────────────────────────────────────
    print("📡 Fetching market data…")
    df = get_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
    price = float(df["close"].iloc[-1])
    print(f"   Current price : ${price:,.2f}")

    # ── 2. Volatility ─────────────────────────────────────────────────────────
    rv = realized_volatility(df)
    iv = (iv_pct / 100) if iv_pct is not None else rv
    em = expected_move(rv, price, horizon)

    print(f"\n📊 Volatility")
    print(f"   Realised Vol (RV) : {rv * 100:.1f}%")
    print(f"   Implied  Vol (IV) : {iv * 100:.1f}%")
    print(f"   Expected Move ({horizon}d): ±${em:,.0f}")

    # ── 3. Signals ────────────────────────────────────────────────────────────
    vs = vol_signal(rv, iv)
    ts = trend_signal(df)

    print(f"\n🎯 Signals")
    print(f"   Vol   signal : {vs}")
    print(f"   Trend signal : {ts}")

    # ── 4. DVOL & Vol Crush ───────────────────────────────────────────────────
    print(f"\n🌋 DVOL & Vol Crush ({dvol_currency}, last {dvol_days}d)")
    try:
        dvol_df  = get_dvol_history(currency=dvol_currency, days=dvol_days)
        metrics  = vol_crush_metrics(dvol_df)
        crush_sig = vol_crush_signal(metrics["crush_detected"], metrics["current"])

        print(f"   Current DVOL   : {metrics['current']:.1f}%")
        print(f"   30d avg DVOL   : {metrics['avg_30d']:.1f}%")
        print(f"   vs avg         : {metrics['pct_from_avg'] * 100:+.1f}%")
        print(f"   1d change      : {metrics['drop_1d'] * 100:+.1f}%")
        print(f"   7d change      : {metrics['drop_7d'] * 100:+.1f}%")
        print(f"   Vol regime     : {'ELEVATED' if metrics['is_elevated'] else 'NORMAL'}")
        print(f"   Crush detected : {metrics['crush_detected']}")
        print(f"\n   ⚡ Signal       : {crush_sig['signal']}")
        print(f"   Strategy       : {crush_sig['strategy']}")
        print(f"   Confidence     : {crush_sig['confidence']}")
        print(f"   Rationale      : {crush_sig['rationale']}")
    except Exception as exc:
        print(f"   ⚠️  Could not fetch DVOL: {exc}")

    # ── 5. Probabilities ──────────────────────────────────────────────────────
    target_up   = price * 1.05
    target_down = price * 0.95

    p_up    = probability_move(price, target_up,   rv, horizon)
    p_down  = probability_move(price, target_down, rv, horizon)
    p_range = probability_range(price, target_down, target_up, rv, horizon)

    print(f"\n🧮 Probabilities (horizon = {horizon}d, using RV)")
    print(f"   P(price ≥ {target_up:,.0f}) = {p_up:.2%}")
    print(f"   P(price ≤ {target_down:,.0f}) = {p_down:.2%}")
    print(f"   P(price in [{target_down:,.0f} – {target_up:,.0f}]) = {p_range:.2%}")

    print(f"\n{'=' * 60}\n")

    # ── 6. Event Driven Strategy ──────────────────────────────────────────────
    print("📅 Event Driven Strategy")
    events = get_upcoming_events()
    event_signals = event_proximity_signal(events)

    if event_signals:
        for es in event_signals:
            print(
                f"   {es['signal']:40s}  "
                f"{es['event']:20s}  J-{es['dte']}  impact={es['impact']}"
            )
    else:
        print("   Aucun événement dans la fenêtre 0–7 jours.")

    final_sig = event_driven_signal(
        {"signal": vs, "confidence": "MEDIUM", "reason": "Base vol signal"},
        event_signals,
    )
    print(f"\n   ⚡ Signal final  : {final_sig.get('signal', '—')}")
    print(f"   Confidence      : {final_sig.get('confidence', '—')}")
    print(f"   Raison          : {final_sig.get('reason', final_sig.get('rationale', '—'))}")

    print(f"\n{'=' * 60}\n")


def main() -> None:
    args = parse_args()

    if args.schedule:
        from automation.scheduler import start_scheduler  # noqa: PLC0415
        start_scheduler(args.interval)
    else:
        run(
            symbol=args.symbol,
            timeframe=args.timeframe,
            limit=args.limit,
            iv_pct=args.iv,
            horizon=args.horizon,
            dvol_currency=args.dvol_currency,
            dvol_days=args.dvol_days,
        )


if __name__ == "__main__":
    main()
