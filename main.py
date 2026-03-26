#!/usr/bin/env python3
# main.py
# Orchestrator — runs a full analytical cycle from the command line.
#
# Usage:
#   python main.py
#   python main.py --symbol ETH/USDT --timeframe 4h

import argparse

from config.settings import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, DEFAULT_LIMIT
from data.market_data import get_ohlcv
from analytics.volatility import realized_volatility, expected_move
from analytics.signals import vol_signal, trend_signal
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
    return parser.parse_args()


def run(symbol: str, timeframe: str, limit: int, iv_pct: float | None, horizon: float) -> None:
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

    # ── 4. Probabilities ──────────────────────────────────────────────────────
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


def main() -> None:
    args = parse_args()
    run(
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
        iv_pct=args.iv,
        horizon=args.horizon,
    )


if __name__ == "__main__":
    main()
