# models/probability.py
# Probabilistic price-move models based on the log-normal distribution.

import numpy as np
from scipy.stats import norm


def probability_move(
    current_price: float,
    target_price: float,
    vol: float,
    horizon_days: float = 1,
) -> float:
    """Return the probability that price reaches *target_price* within *horizon_days*.

    Uses the log-normal (Black-Scholes) framework.  For a call-side target
    (target > current) this returns P(S_T ≥ target).  For a put-side target
    (target < current) this returns P(S_T ≤ target).

    Args:
        current_price: Today's spot price.
        target_price:  The price level to evaluate.
        vol:           Annualised volatility (decimal, e.g. ``0.65``).
        horizon_days:  Time horizon in calendar days.

    Returns:
        Probability in [0, 1].
    """
    # 1-σ move in price terms
    sigma = current_price * vol * np.sqrt(horizon_days / 365)

    # Standardised z-score (positive = upside target)
    z = (target_price - current_price) / sigma

    if target_price >= current_price:
        # P(S_T >= target)
        return float(1 - norm.cdf(z))
    else:
        # P(S_T <= target)
        return float(norm.cdf(z))


def probability_range(
    current_price: float,
    lower: float,
    upper: float,
    vol: float,
    horizon_days: float = 1,
) -> float:
    """Return the probability that price stays within [lower, upper].

    Args:
        current_price: Today's spot price.
        lower:         Lower bound of the price range.
        upper:         Upper bound of the price range.
        vol:           Annualised volatility (decimal).
        horizon_days:  Time horizon in calendar days.

    Returns:
        Probability in [0, 1].
    """
    sigma = current_price * vol * np.sqrt(horizon_days / 365)

    z_lower = (lower - current_price) / sigma
    z_upper = (upper - current_price) / sigma

    return float(norm.cdf(z_upper) - norm.cdf(z_lower))
