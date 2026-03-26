# models/greeks.py
# Black-Scholes Greeks: Delta, Vega, Theta.

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _validate_inputs(S: float, K: float, T: float, sigma: float) -> None:
    """Raise ``ValueError`` for degenerate Black-Scholes inputs."""
    if S <= 0:
        raise ValueError(f"Spot price S must be positive, got {S}.")
    if K <= 0:
        raise ValueError(f"Strike price K must be positive, got {K}.")
    if T <= 0:
        raise ValueError(f"Time to expiry T must be > 0, got {T}.")
    if sigma <= 0:
        raise ValueError(f"Volatility sigma must be > 0, got {sigma}.")


def d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes d1 intermediate value.

    Args:
        S:     Spot price (must be positive).
        K:     Strike price (must be positive).
        T:     Time to expiry in years (must be > 0).
        r:     Risk-free rate (decimal, e.g. ``0.05``).
        sigma: Implied volatility (decimal, e.g. ``0.70``, must be > 0).

    Returns:
        d1 scalar.

    Raises:
        ValueError: If *S*, *K*, *T*, or *sigma* are non-positive.
    """
    _validate_inputs(S, K, T, sigma)
    return (np.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * np.sqrt(T))


def d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes d2 intermediate value.

    Args:
        S:     Spot price (must be positive).
        K:     Strike price (must be positive).
        T:     Time to expiry in years (must be > 0).
        r:     Risk-free rate (decimal).
        sigma: Implied volatility (decimal, must be > 0).

    Returns:
        d2 scalar.

    Raises:
        ValueError: If *S*, *K*, *T*, or *sigma* are non-positive.
    """
    return d1(S, K, T, r, sigma) - sigma * np.sqrt(T)


def delta_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Delta of a European call option.

    Measures the sensitivity of the call price to a $1 change in spot price.
    Range: [0, 1].  At-the-money calls have delta ≈ 0.5.

    Args:
        S:     Spot price (must be positive).
        K:     Strike price (must be positive).
        T:     Time to expiry in years (must be > 0).
        r:     Risk-free rate (decimal).
        sigma: Implied volatility (decimal, must be > 0).

    Returns:
        Delta in [0, 1].

    Raises:
        ValueError: If *S*, *K*, *T*, or *sigma* are non-positive.
    """
    return float(norm.cdf(d1(S, K, T, r, sigma)))


def delta_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Delta of a European put option.

    Measures the sensitivity of the put price to a $1 change in spot price.
    Range: [-1, 0].  At-the-money puts have delta ≈ −0.5.

    Args:
        S:     Spot price (must be positive).
        K:     Strike price (must be positive).
        T:     Time to expiry in years (must be > 0).
        r:     Risk-free rate (decimal).
        sigma: Implied volatility (decimal, must be > 0).

    Returns:
        Delta in [-1, 0].

    Raises:
        ValueError: If *S*, *K*, *T*, or *sigma* are non-positive.
    """
    return float(norm.cdf(d1(S, K, T, r, sigma)) - 1)


def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Vega of a European option (identical for calls and puts).

    Measures the sensitivity of the option price to a 1-unit (decimal) change
    in implied volatility.  Multiply by 0.01 (or divide by 100) to obtain the
    price change for a 1 percentage-point move in IV.

    Args:
        S:     Spot price (must be positive).
        K:     Strike price (must be positive).
        T:     Time to expiry in years (must be > 0).
        r:     Risk-free rate (decimal).
        sigma: Implied volatility (decimal, must be > 0).

    Returns:
        Vega ($ per 1-unit decimal vol change; divide by 100 for $ per 1% point).

    Raises:
        ValueError: If *S*, *K*, *T*, or *sigma* are non-positive.
    """
    return float(S * norm.pdf(d1(S, K, T, r, sigma)) * np.sqrt(T))


def theta_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Theta of a European call option (time decay per year).

    Returns a negative value: the call loses value as time passes.
    Divide by 365 to obtain daily theta.

    Args:
        S:     Spot price (must be positive).
        K:     Strike price (must be positive).
        T:     Time to expiry in years (must be > 0).
        r:     Risk-free rate (decimal).
        sigma: Implied volatility (decimal, must be > 0).

    Returns:
        Theta ($ per year; negative for long positions).

    Raises:
        ValueError: If *S*, *K*, *T*, or *sigma* are non-positive.
    """
    _d1 = d1(S, K, T, r, sigma)
    _d2 = d2(S, K, T, r, sigma)
    term1 = -(S * norm.pdf(_d1) * sigma) / (2 * np.sqrt(T))
    term2 = -r * K * np.exp(-r * T) * norm.cdf(_d2)
    return float(term1 + term2)
