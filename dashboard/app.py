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
)
from data.market_data import get_ohlcv
from analytics.volatility import realized_volatility, expected_move, rolling_realized_volatility
from analytics.signals import vol_signal, trend_signal
from models.probability import probability_move, probability_range

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

st.subheader("📉 Rolling Realised Volatility (24-candle)")
rv_series = rolling_realized_volatility(df, window=24) * 100   # → %
st.line_chart(rv_series.dropna(), use_container_width=True)

# ── Raw data ──────────────────────────────────────────────────────────────────
with st.expander("🗃️ Raw OHLCV data"):
    st.dataframe(df.tail(50), use_container_width=True)
