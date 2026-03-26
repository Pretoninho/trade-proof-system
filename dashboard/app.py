# dashboard/app.py
# Streamlit dashboard — Mini Bloomberg Crypto Terminal
#
# Run with:
#   streamlit run dashboard/app.py

import streamlit as st
import pandas as pd

from config.settings import (
    DASHBOARD_TITLE,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    DEFAULT_LIMIT,
    DEFAULT_TARGET_PRICE_OFFSET,
    DERIBIT_CURRENCY,
    RV_ROLLING_WINDOW,
)
from data.market_data import get_ohlcv
from data.options_data import get_dvol_history
from analytics.volatility import realized_volatility, expected_move, rolling_realized_volatility
from analytics.signals import vol_signal, trend_signal, vol_crush_signal
from analytics.vol_crush import vol_crush_metrics
from models.probability import probability_move, probability_range
from models.backtest import backtest_vol_strategy, performance_metrics

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=DASHBOARD_TITLE,
    page_icon="📊",
    layout="wide",
)

st.title(f"📊 {DASHBOARD_TITLE}")

# ── Sidebar — user controls ───────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    symbol    = st.text_input("Symbol",    value=DEFAULT_SYMBOL)
    timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
    limit     = st.slider("Candles", min_value=50, max_value=1000, value=DEFAULT_LIMIT, step=50)
    dvol_currency = st.selectbox("DVOL Currency", ["BTC", "ETH"], index=0)
    dvol_history_days = st.slider("DVOL History (days)", min_value=7, max_value=90, value=30)
    implied_vol_pct = st.number_input(
        "Implied Volatility — IV % (annualised)",
        min_value=0.0,
        max_value=500.0,
        value=70.0,
        step=1.0,
        help="Enter the current implied volatility from Deribit DVOL or any options pricer.",
    )
    horizon_days = st.slider("Horizon (days)", min_value=1, max_value=30, value=1)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching market data…"):
    try:
        df = get_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
    except Exception as exc:
        st.error(f"Failed to fetch data: {exc}")
        st.stop()

price = float(df["close"].iloc[-1])
vol   = realized_volatility(df)
iv    = implied_vol_pct / 100  # convert % → decimal

# ── Key metrics ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

em = expected_move(vol, price, horizon_days)

col1.metric(f"{symbol} Price", f"${price:,.2f}")
col2.metric("Realised Vol (RV)", f"{vol * 100:.1f}%")
col3.metric("Implied Vol (IV)",  f"{iv * 100:.1f}%")
col4.metric(f"Expected Move ({horizon_days}d)", f"±${em:,.0f}")

# ── Signals ───────────────────────────────────────────────────────────────────
st.subheader("🎯 Signals")

sig_col1, sig_col2 = st.columns(2)

vs = vol_signal(vol, iv)
ts = trend_signal(df)

vol_color   = "🟢" if vs == "BUY VOL"  else ("🔴" if vs == "SELL VOL" else "⚪")
trend_color = "🟢" if ts == "BULLISH"  else ("🔴" if ts == "BEARISH"  else "⚪")

sig_col1.metric("Vol Signal",   f"{vol_color} {vs}")
sig_col2.metric("Trend Signal", f"{trend_color} {ts}")

# ── DVOL & Vol Crush ──────────────────────────────────────────────────────────
st.subheader(f"🌋 DVOL & Vol Crush — {dvol_currency}")

with st.spinner(f"Fetching {dvol_currency} DVOL history ({dvol_history_days}d)…"):
    try:
        dvol_df = get_dvol_history(currency=dvol_currency, days=dvol_history_days)
    except Exception as exc:
        st.error(f"Failed to fetch DVOL: {exc}")
        dvol_df = None

if dvol_df is not None and not dvol_df.empty:
    metrics = vol_crush_metrics(dvol_df)
    crush_sig = vol_crush_signal(metrics["crush_detected"], metrics["current"])

    # ── DVOL key metrics ──────────────────────────────────────────────────
    dv_col1, dv_col2, dv_col3, dv_col4 = st.columns(4)

    dv_col1.metric(
        f"DVOL {dvol_currency} (current)",
        f"{metrics['current']:.1f}%",
        delta=f"{metrics['drop_1d'] * 100:.1f}% (1d)",
    )
    dv_col2.metric(
        "DVOL 30d avg",
        f"{metrics['avg_30d']:.1f}%",
        delta=f"{metrics['pct_from_avg'] * 100:+.1f}% vs avg",
    )
    dv_col3.metric(
        "7d change",
        f"{metrics['drop_7d'] * 100:+.1f}%",
    )
    regime_label = "🔴 Elevated" if metrics["is_elevated"] else "🟢 Normal"
    dv_col4.metric("Vol Regime", regime_label)

    # ── Vol crush signal ──────────────────────────────────────────────────
    crush_color = {
        "HIGH":   "🔴",
        "MEDIUM": "🟡",
        "LOW":    "⚪",
    }.get(crush_sig["confidence"], "⚪")

    cs_col1, cs_col2, cs_col3 = st.columns(3)
    cs_col1.metric("Signal",     f"{crush_color} {crush_sig['signal']}")
    cs_col2.metric("Strategy",   crush_sig["strategy"])
    cs_col3.metric("Confidence", crush_sig["confidence"])

    st.caption(f"💡 {crush_sig['rationale']}")

    # ── DVOL vs Realised Vol chart ─────────────────────────────────────────
    st.subheader("📉 DVOL vs Realised Volatility")

    rv_daily = (
        rolling_realized_volatility(df, window=RV_ROLLING_WINDOW)
        .resample("1D")
        .last()
        .dropna()
        * 100  # → %
    )
    dvol_close = dvol_df["close"]

    combined = pd.DataFrame({
        f"DVOL {dvol_currency}":   dvol_close,
        "Realised Vol 24h (%)": rv_daily,
    }).dropna(how="all")

    if not combined.empty:
        st.line_chart(combined, use_container_width=True)

    with st.expander(f"🗃️ Raw DVOL data ({dvol_currency})"):
        st.dataframe(dvol_df.tail(30), use_container_width=True)

# ── Probability calculator ────────────────────────────────────────────────────
st.subheader("🧮 Probability Calculator")

prob_col1, prob_col2 = st.columns(2)

with prob_col1:
    st.markdown("**Single-target probability**")
    default_target = round(price * (1 + DEFAULT_TARGET_PRICE_OFFSET), 2)
    target = st.number_input(
        "Target price",
        min_value=0.01,
        value=default_target,
        step=100.0,
        format="%.2f",
    )
    if target:
        prob = probability_move(price, target, vol, horizon_days)
        direction = "above" if target >= price else "below"
        st.success(f"P(price {direction} {target:,.2f}) = **{prob:.2%}**")

with prob_col2:
    st.markdown("**Range probability**")
    lower_default = round(price * 0.95, 2)
    upper_default = round(price * 1.05, 2)
    lower = st.number_input("Lower bound", min_value=0.01, value=lower_default, step=100.0, format="%.2f")
    upper = st.number_input("Upper bound", min_value=0.01, value=upper_default, step=100.0, format="%.2f")
    if lower < upper:
        prob_range = probability_range(price, lower, upper, vol, horizon_days)
        st.success(f"P(price in [{lower:,.0f} – {upper:,.0f}]) = **{prob_range:.2%}**")
    else:
        st.warning("Lower bound must be less than upper bound.")

# ── Charts ────────────────────────────────────────────────────────────────────
st.subheader("📈 Price Chart")
st.line_chart(df["close"], use_container_width=True)

st.subheader(f"📉 Rolling Realised Volatility ({RV_ROLLING_WINDOW}-candle)")
rv_series = rolling_realized_volatility(df, window=RV_ROLLING_WINDOW) * 100   # → %
st.line_chart(rv_series.dropna(), use_container_width=True)

# ── Raw data ──────────────────────────────────────────────────────────────────
with st.expander("🗃️ Raw OHLCV data"):
    st.dataframe(df.tail(50), use_container_width=True)

# ── Backtest ──────────────────────────────────────────────────────────────────
st.header("📐 Backtest Strategy")

# Use the live DVOL snapshot as a constant proxy when real historical DVOL is
# unavailable.  Replace with a true historical DVOL series for production use.
if dvol_df is not None and not dvol_df.empty:
    # Align historical DVOL to the price DataFrame by repeating the last value
    # for any missing bars — a conservative fallback.
    dvol_close_aligned = [float(dvol_df["close"].iloc[-1])] * len(df)
else:
    dvol_close_aligned = [implied_vol_pct] * len(df)

with st.spinner("Running backtest…"):
    pnl_series = backtest_vol_strategy(df, dvol_close_aligned)
    stats = performance_metrics(pnl_series)

st.subheader("📊 Performance")

bt_col1, bt_col2, bt_col3, bt_col4 = st.columns(4)
bt_col1.metric("Trades",       stats["trades"])
bt_col2.metric("Winrate",      f"{stats['winrate']:.2%}")
bt_col3.metric("PnL total",    stats["pnl_total"])
bt_col4.metric("Max Drawdown", f"{stats['max_drawdown']:.0f}")

st.line_chart(pnl_series.cumsum(), use_container_width=True)

st.caption(
    "⚠️ Simplified backtest: +1 / −1 scoring, no real option pricing, "
    "no skew, no expiration. DVOL is the current snapshot repeated — "
    "replace with real historical DVOL for production-grade results."
)
