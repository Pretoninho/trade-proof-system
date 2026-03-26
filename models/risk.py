# models/risk.py
# Position sizing and risk management utilities.

from __future__ import annotations


def position_size(
    account_size: float,
    risk_per_trade: float,
    stop_loss_pct: float,
) -> float:
    """Compute the recommended position size using fixed-fractional risk.

    Scales the notional so that if the stop-loss triggers the total loss equals
    exactly ``risk_per_trade`` of the account.

    Args:
        account_size:    Total account equity.
        risk_per_trade:  Fraction of capital to risk per trade (e.g. ``0.02`` = 2 %).
        stop_loss_pct:   Maximum expected loss per unit as a decimal (e.g. ``0.05`` = 5 %).

    Returns:
        Recommended position size (same units as *account_size*).

    Raises:
        ValueError: If *stop_loss_pct* is zero or negative.
    """
    if stop_loss_pct <= 0:
        raise ValueError(f"stop_loss_pct must be > 0, got {stop_loss_pct}.")
    risk_amount = account_size * risk_per_trade
    return risk_amount / stop_loss_pct


def vol_adjusted_size(
    account_size: float,
    vol: float,
    base_risk: float = 0.02,
) -> float:
    """Compute a volatility-adjusted position size.

    Scales risk down in high-vol regimes and up in low-vol regimes to keep
    dollar-risk roughly constant regardless of market conditions.

    Decision rules:

    * ``vol > 1``   (> 100 % annualised) → halve the base risk (dangerous regime).
    * ``vol < 0.5`` (< 50 % annualised)  → 1.5× the base risk (calm regime).
    * Otherwise → use *base_risk* as-is.

    Args:
        account_size: Total account equity.
        vol:          Annualised implied or realised volatility (decimal).
        base_risk:    Base risk fraction applied to *account_size* (default 2 %).

    Returns:
        Recommended position size (same units as *account_size*).
    """
    if vol > 1:
        return account_size * (base_risk / 2)

    if vol < 0.5:
        return account_size * (base_risk * 1.5)

    return account_size * base_risk
