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
from analytics.signals import vol_signal, trend_signal, vol_crush_signal, event_driven_signal
from analytics.vol_crush import vol_crush_metrics
from analytics.event_analysis import event_proximity_signal
from data.events_data import get_upcoming_events
from models.probability import probability_move, probability_range
from models.backtest import backtest_vol_strategy, performance_metrics
from models.greeks import delta_call, vega
from models.risk import position_size
from models.tracking import create_signal_record, update_trade
from models.scoring import compute_score, performance_by_signal
from storage.database import save_signal, load_signals, DB_FILE
from dashboard.layout import display_header, display_metrics, display_signal
from dashboard.charts import (
    plot_price_with_strikes,
    plot_vol_comparison,
    plot_equity_curve,
    plot_dvol_series,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=DASHBOARD_TITLE,
    page_icon="📊",
    layout="wide",
)

display_header()

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
from config.settings import EXCHANGE_FALLBACKS  # noqa: E402

with st.spinner("Fetching market data…"):
    try:
        df = get_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
    except Exception as exc:
        # Build the same candidate list that get_ohlcv() would have tried.
        _tried = ["binance"] + [e for e in EXCHANGE_FALLBACKS if e != "binance"]
        st.error(
            f"Could not fetch market data for **{symbol}** from any available exchange "
            f"({', '.join(_tried)}).\n\n**Details:** {exc}"
        )
        st.stop()

price = float(df["close"].iloc[-1])
vol   = realized_volatility(df)
iv    = implied_vol_pct / 100  # convert % → decimal

vs = vol_signal(vol, iv)
ts = trend_signal(df)

# ── Compute signals early (needed by multiple sections) ───────────────────────
events = get_upcoming_events()
event_signals = event_proximity_signal(events)
final_signal = event_driven_signal(
    {"signal": vs, "confidence": "MEDIUM", "reason": "Base vol signal"},
    event_signals,
)

# ── Top-line metrics & signal badge ──────────────────────────────────────────
display_metrics(price, vol, iv)

em = expected_move(vol, price, horizon_days)
st.caption(
    f"Expected move ({horizon_days}d): **±${em:,.0f}** · "
    f"Trend: {'🟢 BULLISH' if ts == 'BULLISH' else ('🔴 BEARISH' if ts == 'BEARISH' else '⚪ NEUTRAL')}"
)

final_sig_label    = final_signal.get("signal", vs)
final_confidence   = final_signal.get("confidence", "MEDIUM")
final_strategy     = final_signal.get("strategy", "—")
display_signal({
    "signal":     final_sig_label,
    "strategy":   final_strategy,
    "confidence": final_confidence,
})

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 🟢 BLOC 1 — MARKET STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════
st.header("🟢 1. Market Structure")
st.caption("Où est le prix ? Où sont tes strikes ?")

strike_call = price * 1.05
strike_put  = price * 0.95

fig_price = plot_price_with_strikes(
    df.reset_index().rename(columns={"index": "timestamp"}),
    strike_call=strike_call,
    strike_put=strike_put,
)
st.pyplot(fig_price)

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
        range_prob = probability_range(price, lower, upper, vol, horizon_days)
        st.success(f"P(price in [{lower:,.0f} – {upper:,.0f}]) = **{range_prob:.2%}**")
    else:
        st.warning("Lower bound must be less than upper bound.")

with st.expander("🗃️ Raw OHLCV data"):
    st.dataframe(df.tail(50), use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 🟡 BLOC 2 — VOLATILITY EDGE
# ═══════════════════════════════════════════════════════════════════════════════
st.header("🟡 2. Volatility Edge")
st.caption("IV > RV ? DVOL monte ou chute ? → décision.")

# ── RV vs IV bar chart ────────────────────────────────────────────────────────
edge_col1, edge_col2 = st.columns([1, 2])

with edge_col1:
    fig_vol = plot_vol_comparison(vol, iv)
    st.pyplot(fig_vol)

with edge_col2:
    # ── DVOL & Vol Crush ──────────────────────────────────────────────────
    with st.spinner(f"Fetching {dvol_currency} DVOL history ({dvol_history_days}d)…"):
        try:
            dvol_df = get_dvol_history(currency=dvol_currency, days=dvol_history_days)
        except Exception as exc:
            st.error(f"Failed to fetch DVOL: {exc}")
            dvol_df = None

    if dvol_df is not None and not dvol_df.empty:
        metrics = vol_crush_metrics(dvol_df)
        crush_sig = vol_crush_signal(metrics["crush_detected"], metrics["current"])

        dv_col1, dv_col2, dv_col3, dv_col4 = st.columns(4)
        dv_col1.metric(
            f"DVOL {dvol_currency}",
            f"{metrics['current']:.1f}%",
            delta=f"{metrics['drop_1d'] * 100:.1f}% (1d)",
        )
        dv_col2.metric(
            "30d avg",
            f"{metrics['avg_30d']:.1f}%",
            delta=f"{metrics['pct_from_avg'] * 100:+.1f}%",
        )
        dv_col3.metric("7d change", f"{metrics['drop_7d'] * 100:+.1f}%")
        regime_label = "🔴 Elevated" if metrics["is_elevated"] else "🟢 Normal"
        dv_col4.metric("Regime", regime_label)

        crush_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}.get(
            crush_sig["confidence"], "⚪"
        )
        cs_col1, cs_col2, cs_col3 = st.columns(3)
        cs_col1.metric("Signal",     f"{crush_color} {crush_sig['signal']}")
        cs_col2.metric("Strategy",   crush_sig["strategy"])
        cs_col3.metric("Confidence", crush_sig["confidence"])
        st.caption(f"💡 {crush_sig['rationale']}")

# ── DVOL time-series chart ────────────────────────────────────────────────────
if dvol_df is not None and not dvol_df.empty:
    fig_dvol = plot_dvol_series(dvol_df["close"].values)
    st.pyplot(fig_dvol)

    rv_daily = (
        rolling_realized_volatility(df, window=RV_ROLLING_WINDOW)
        .resample("1D")
        .last()
        .dropna()
        * 100
    )
    combined = pd.DataFrame({
        f"DVOL {dvol_currency}": dvol_df["close"],
        "Realised Vol 24h (%)":  rv_daily,
    }).dropna(how="all")
    if not combined.empty:
        st.subheader("📉 DVOL vs Realised Volatility")
        st.line_chart(combined, use_container_width=True)

    with st.expander(f"🗃️ Raw DVOL data ({dvol_currency})"):
        st.dataframe(dvol_df.tail(30), use_container_width=True)

# ── Rolling RV series ─────────────────────────────────────────────────────────
st.subheader(f"📉 Rolling Realised Volatility ({RV_ROLLING_WINDOW}-candle)")
rv_series = rolling_realized_volatility(df, window=RV_ROLLING_WINDOW) * 100
st.line_chart(rv_series.dropna(), use_container_width=True)

# ── Event Driven ──────────────────────────────────────────────────────────────
with st.expander("📅 Event Driven Details", expanded=False):
    ev_col1, ev_col2 = st.columns(2)

    with ev_col1:
        st.subheader("Événements détectés")
        if event_signals:
            for es in event_signals:
                badge = "🔴" if "POST EVENT" in es["signal"] else "🟡"
                impact_badge = "🔥" if es["impact"] == "HIGH" else "⚡"
                st.write(
                    f"{badge} **{es['event']}** — {es['signal']} "
                    f"(J-{es['dte']}) "
                    f"{impact_badge} {es['impact']}"
                )
        else:
            st.info("Aucun événement dans la fenêtre 0–7 jours.")

    with ev_col2:
        st.subheader("Signal final (event-driven)")
        final_reason = final_signal.get("reason", final_signal.get("rationale", "—"))
        confidence_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}.get(
            final_confidence, "⚪"
        )
        st.metric("Signal",     f"{confidence_color} {final_sig_label}")
        st.metric("Confidence", final_confidence)
        st.caption(f"💡 {final_reason}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 🔵 BLOC 3 — PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════
st.header("🔵 3. Performance")
st.caption("Est-ce que ta stratégie marche ?")

# ── Backtest ──────────────────────────────────────────────────────────────────
st.subheader("📐 Backtest Strategy")

if dvol_df is not None and not dvol_df.empty:
    dvol_close_aligned = [float(dvol_df["close"].iloc[-1])] * len(df)
else:
    dvol_close_aligned = [implied_vol_pct] * len(df)

with st.spinner("Running backtest…"):
    pnl_series = backtest_vol_strategy(df, dvol_close_aligned)
    bt_stats = performance_metrics(pnl_series)

bt_col1, bt_col2, bt_col3, bt_col4 = st.columns(4)
bt_col1.metric("Trades",       bt_stats["trades"])
bt_col2.metric("Winrate",      f"{bt_stats['winrate']:.2%}")
bt_col3.metric("PnL total",    bt_stats["pnl_total"])
bt_col4.metric("Max Drawdown", f"{bt_stats['max_drawdown']:.0f}")

fig_equity = plot_equity_curve(pnl_series)
st.pyplot(fig_equity)

st.caption(
    "⚠️ Simplified backtest: +1 / −1 scoring, no real option pricing, "
    "no skew, no expiration. DVOL is the current snapshot repeated — "
    "replace with real historical DVOL for production-grade results."
)

# ── Track Record ──────────────────────────────────────────────────────────────
st.subheader("🏆 Track Record")

with st.expander("➕ Log a new signal", expanded=False):
    with st.form("log_signal_form"):
        log_price    = st.number_input("Entry price", min_value=0.01, value=float(price), format="%.2f")
        log_signal   = st.selectbox("Signal", ["SELL VOL", "BUY VOL", "NEUTRAL"])
        log_strategy = st.selectbox("Strategy", ["vol_crush", "event", "backtest", "manual"])
        submitted    = st.form_submit_button("Save signal")

    if submitted:
        record = create_signal_record(log_price, log_signal, log_strategy)
        save_signal(record)
        st.success("Signal saved ✅")

df_signals = load_signals()

if not df_signals.empty:
    open_mask = df_signals["pnl"].isna()
    if open_mask.any():
        st.subheader("📤 Close an open trade")
        open_indices = df_signals.index[open_mask].tolist()
        selected_idx = st.selectbox(
            "Select trade to close (row index)",
            options=open_indices,
            format_func=lambda i: (
                f"#{i} — {df_signals.loc[i, 'date']}  "
                f"{df_signals.loc[i, 'signal']} @ {df_signals.loc[i, 'price_entry']}"
            ),
        )
        exit_price = st.number_input(
            "Exit price", min_value=0.01, value=float(price), format="%.2f", key="exit_price"
        )
        if st.button("Close trade"):
            entry  = float(df_signals.loc[selected_idx, "price_entry"])
            signal = str(df_signals.loc[selected_idx, "signal"])
            if "SELL" in signal.upper():
                pnl = entry - exit_price
            else:
                pnl = exit_price - entry
            df_signals = update_trade(df_signals, selected_idx, exit_price, pnl)
            df_signals.to_csv(DB_FILE, index=False)
            st.success(f"Trade #{selected_idx} closed — PnL: {pnl:+.2f} ✅")
            st.rerun()

    tr_stats = compute_score(df_signals)

    if tr_stats["trades"] > 0:
        st.subheader("📊 Performance scorecard")
        sc_col1, sc_col2, sc_col3, sc_col4 = st.columns(4)
        sc_col1.metric("Trades",    tr_stats["trades"])
        sc_col2.metric("Winrate",   f"{tr_stats['winrate']:.2%}")
        sc_col3.metric("PnL total", f"{tr_stats['total_pnl']:+.2f}")
        sc_col4.metric("Avg PnL",   f"{tr_stats['avg_pnl']:+.2f}")

        sc_col5, sc_col6, sc_col7, sc_col8 = st.columns(4)
        sc_col5.metric(
            "Sharpe",
            f"{tr_stats['sharpe']:.2f}" if tr_stats["sharpe"] is not None else "—",
        )
        sc_col6.metric("Max Drawdown", f"{tr_stats['max_drawdown']:.2f}")
        pf_label = (
            "∞" if tr_stats["profit_factor"] == float("inf")
            else f"{tr_stats['profit_factor']:.2f}"
        )
        sc_col7.metric("Profit Factor", pf_label)
        sc_col8.metric("Expectancy",    f"{tr_stats['expectancy']:+.2f}")

        closed_pnl = (
            df_signals.dropna(subset=["pnl"])
            .assign(pnl=lambda d: pd.to_numeric(d["pnl"], errors="coerce"))
            .dropna(subset=["pnl"])
        )
        if not closed_pnl.empty:
            fig_tr_equity = plot_equity_curve(closed_pnl["pnl"])
            st.pyplot(fig_tr_equity)

            # ── Performance by signal type ─────────────────────────────────────
            by_sig = performance_by_signal(df_signals)
            if not by_sig.empty:
                st.subheader("📈 Performance by signal type")
                st.dataframe(
                    by_sig.style.format(
                        {
                            "winrate":   "{:.1%}",
                            "pnl_total": "{:+.2f}",
                            "pnl_avg":   "{:+.2f}",
                        }
                    ),
                    use_container_width=True,
                )
    else:
        st.info("No closed trades yet — log a signal and close it to see your scorecard.")

    with st.expander("🗃️ All signals"):
        st.dataframe(df_signals, use_container_width=True)
else:
    st.info("No signals recorded — use the form above to log your first signal.")

# ── Risk Management ───────────────────────────────────────────────────────────
with st.expander("⚖️ Risk Management", expanded=False):
    rm_col1, rm_col2 = st.columns(2)

    with rm_col1:
        st.subheader("Position Sizing")
        account_size   = st.number_input("Capital ($)", min_value=100.0, value=10_000.0, step=500.0)
        risk_per_trade = st.number_input("Risk per trade (%)", min_value=0.1, max_value=10.0,
                                         value=2.0, step=0.1) / 100
        stop_loss_pct  = st.number_input("Stop-loss (%)", min_value=0.1, max_value=50.0,
                                         value=5.0, step=0.5) / 100
        size = position_size(account_size, risk_per_trade, stop_loss_pct)
        st.metric("Recommended position size", f"${size:,.2f}")
        st.caption(
            f"Risking {risk_per_trade * 100:.1f}% of ${account_size:,.0f} "
            f"with a {stop_loss_pct * 100:.1f}% stop-loss."
        )

    with rm_col2:
        st.subheader("Greeks (ATM, 1-day expiry)")
        time_to_expiry_1d = 1 / 365
        if iv > 0:
            delta_val = delta_call(price, price, time_to_expiry_1d, 0.0, iv)
            vega_val  = vega(price, price, time_to_expiry_1d, 0.0, iv)
            st.metric("Delta (call)", f"{delta_val:.4f}",
                      help="$ change in call price per $1 move in spot.")
            st.metric("Vega", f"{vega_val:.4f}",
                      help="$ change in option price per 1-unit (decimal) change in IV. "
                           "Multiply by 0.01 to get the $ change per 1% point move in IV.")
            st.caption(
                f"ATM strike = ${price:,.2f} | IV = {iv * 100:.1f}% | T = 1 day"
            )
        else:
            st.warning("Set a non-zero Implied Volatility in the sidebar to compute Greeks.")

st.divider()

# ── Run Pipeline ──────────────────────────────────────────────────────────────
st.header("🤖 Run Pipeline")

st.caption(
    "Trigger a full autonomous analysis cycle: data → volatility → signals → "
    "storage → report."
)

if st.button("▶ Lancer analyse"):
    with st.spinner("Running pipeline…"):
        try:
            from automation.pipeline import run_pipeline  # noqa: PLC0415
            pipeline_result = run_pipeline(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                dvol_currency=dvol_currency,
            )
            st.success("Pipeline completed ✅")
            st.subheader("Signal")
            st.json(pipeline_result["signal"])
            st.subheader("Report")
            st.text(pipeline_result["report"])
        except Exception as exc:  # noqa: BLE001
            st.error(f"Pipeline failed: {exc}")
