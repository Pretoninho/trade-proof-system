# dashboard/layout.py
# Reusable Streamlit layout helpers — header, top-line metrics, signal badge.

import streamlit as st


def display_header():
    """Render the dashboard page title."""
    st.title("📊 Trade Proof System")
    st.caption("Market · Edge · Performance — lisible en 5 secondes.")


def display_metrics(price: float, rv: float, iv: float):
    """Display the three key numbers side-by-side.

    Parameters
    ----------
    price : float
        Current spot price.
    rv : float
        Realised volatility expressed as a decimal (e.g. 0.55 = 55 %).
    iv : float
        Implied volatility expressed as a decimal (e.g. 0.72 = 72 %).
    """
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Prix (spot)", f"${price:,.2f}")
    col2.metric("📉 Realized Vol (RV)", f"{rv * 100:.1f}%")
    col3.metric(
        "📈 Implied Vol (IV)",
        f"{iv * 100:.1f}%",
        delta=f"{(iv - rv) * 100:+.1f}% vs RV",
        delta_color="inverse",   # red = IV elevated above RV → sell signal
    )


def display_signal(signal: dict):
    """Render a coloured signal badge.

    Parameters
    ----------
    signal : dict
        Expected keys: ``signal`` (str), ``strategy`` (str),
        ``confidence`` (str — "HIGH" | "MEDIUM" | "LOW").
    """
    sig_label   = signal.get("signal", "—")
    strategy    = signal.get("strategy", "—")
    confidence  = signal.get("confidence", "—")

    # Colour-code by signal direction
    if "SELL" in sig_label.upper():
        badge_color = "🔴"
        banner_color = "#ffd6d6"
    elif "BUY" in sig_label.upper():
        badge_color = "🟢"
        banner_color = "#d6ffd6"
    else:
        badge_color = "⚪"
        banner_color = "#f0f0f0"

    confidence_icon = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "💤"}.get(confidence, "")

    st.markdown(
        f"""
        <div style="background:{banner_color};border-radius:8px;padding:12px 16px;margin-bottom:8px;">
            <span style="font-size:1.3rem;font-weight:700;">{badge_color} {sig_label}</span>
            &nbsp;&nbsp;
            <span style="color:#555;font-size:0.9rem;">Strategy: <b>{strategy}</b></span>
            &nbsp;·&nbsp;
            <span style="color:#555;font-size:0.9rem;">Confidence: <b>{confidence_icon} {confidence}</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
