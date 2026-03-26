# dashboard/charts.py
# Centralised chart helpers — all charts return a matplotlib Figure
# so they can be rendered with st.pyplot(fig) in Streamlit.

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


def _style_ax(ax):
    """Apply minimal, clean styling shared by every chart."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)


def plot_price_with_strikes(df, strike_call=None, strike_put=None):
    """Closing-price line with optional call/put strike levels."""
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(df["timestamp"], df["close"], linewidth=1.5, color="#4C72B0", label="Price")

    if strike_call:
        ax.axhline(strike_call, linestyle="--", linewidth=1, color="#2ca02c",
                   label=f"Call strike  {strike_call:,.0f}")
    if strike_put:
        ax.axhline(strike_put, linestyle="--", linewidth=1, color="#d62728",
                   label=f"Put strike  {strike_put:,.0f}")

    ax.set_title("Market Structure — Price & Strikes", fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(fontsize=8)
    _style_ax(ax)
    fig.tight_layout()
    return fig


def plot_vol_comparison(rv, iv):
    """Bar chart comparing Realised Vol vs Implied Vol."""
    labels = ["Realised Vol (RV)", "Implied Vol (IV)"]
    values = [rv * 100, iv * 100]
    colors = ["#4C72B0", "#d62728" if iv > rv else "#2ca02c"]

    fig, ax = plt.subplots(figsize=(5, 3))
    bars = ax.bar(labels, values, color=colors, width=0.5)
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
    ax.set_ylabel("Volatility (%)")
    ax.set_title("Volatility Edge — RV vs IV", fontweight="bold")
    ax.set_ylim(0, max(values) * 1.25)
    _style_ax(ax)
    fig.tight_layout()
    return fig


def plot_equity_curve(pnl_series):
    """Cumulative PnL equity curve with colour-coded positive/negative fill."""
    equity = pnl_series.cumsum()

    fig, ax = plt.subplots(figsize=(10, 3))
    color = "#2ca02c" if equity.iloc[-1] >= 0 else "#d62728"
    ax.plot(equity.values, linewidth=1.5, color=color)
    ax.axhline(0, linewidth=0.8, linestyle="--", color="#888888")
    ax.fill_between(range(len(equity)), equity.values, 0,
                    alpha=0.15, color=color)
    ax.set_title("Performance — Equity Curve", fontweight="bold")
    ax.set_ylabel("Cumulative PnL")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.2f}"))
    _style_ax(ax)
    fig.tight_layout()
    return fig


def plot_dvol_series(dvol_series):
    """DVOL / implied-vol time-series line chart."""
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(dvol_series, linewidth=1.5, color="#9467bd")
    ax.set_title("Volatility Edge — DVOL Evolution", fontweight="bold")
    ax.set_ylabel("DVOL (%)")
    _style_ax(ax)
    fig.tight_layout()
    return fig
