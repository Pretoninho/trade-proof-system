# data/options_data.py
# Fetch options / volatility data from the Deribit public REST API.
#
# Deribit exposes a free, unauthenticated REST API for market data:
#   Base URL : https://www.deribit.com/api/v2
#   Endpoints used:
#     GET /public/get_volatility_index_data  — DVOL OHLC time-series
#     GET /public/get_instruments            — active instrument list
#     GET /public/ticker                     — per-instrument snapshot
#
# Rate limits (public REST, per IP):
#   ~20 requests / second sustained; burst up to 200 credits.
#   Each standard request costs 1 credit (20 credits/s refill rate).
#   Exceeding the limit returns HTTP 429 / error code "too_many_requests".
#   Reference: https://docs.deribit.com/articles/rate-limits

import time

import requests
import pandas as pd

from config.settings import DERIBIT_BASE_URL, DERIBIT_CURRENCY


def _get(endpoint: str, params: dict | None = None) -> dict:
    """Perform a GET request to the Deribit public API."""
    url = f"{DERIBIT_BASE_URL}/public/{endpoint}"
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()["result"]


def get_dvol(currency: str = DERIBIT_CURRENCY) -> float:
    """Return the current Deribit Volatility Index (DVOL) for *currency*.

    DVOL is Deribit's implied-volatility index, analogous to the VIX for
    crypto.  It is expressed as an **annualised percentage** (e.g. 65.2).

    Uses a 2-day rolling window at daily resolution so that only the minimum
    required data is transferred over the wire.

    Endpoint: ``GET /public/get_volatility_index_data``

    Args:
        currency: ``"BTC"`` or ``"ETH"``.

    Returns:
        DVOL value as a float (annualised %).
    """
    now      = pd.Timestamp.utcnow()
    end_ms   = int(now.timestamp() * 1_000)
    start_ms = int((now - pd.Timedelta(days=2)).timestamp() * 1_000)

    data = _get("get_volatility_index_data", {
        "currency":        currency,
        "start_timestamp": start_ms,
        "end_timestamp":   end_ms,
        "resolution":      "1D",
    })
    # The API returns a list of [timestamp (ms), open, high, low, close] arrays.
    # We return the most-recent close value.
    return float(data["data"][-1][4])


def get_dvol_history(
    currency: str = DERIBIT_CURRENCY,
    days: int = 30,
    resolution: str = "1D",
) -> pd.DataFrame:
    """Return a historical DVOL time-series as a DataFrame.

    Fetches the last *days* calendar days of DVOL data from Deribit at the
    requested *resolution*.  Useful for vol-crush detection and for comparing
    implied vol against realised vol over time.

    Endpoint: ``GET /public/get_volatility_index_data``

    Args:
        currency:   ``"BTC"`` or ``"ETH"``.
        days:       How many calendar days of history to retrieve (default 30).
        resolution: Candle resolution in full seconds or the keyword ``"1D"``.
                    Supported values: ``"1"`` (1 s), ``"60"`` (1 min),
                    ``"3600"`` (1 h), ``"43200"`` (12 h), ``"1D"`` (1 day).

    Returns:
        DataFrame indexed by UTC timestamp with columns:
        ``open``, ``high``, ``low``, ``close``.
        ``close`` is the DVOL value at the end of each period (annualised %).
    """
    now      = pd.Timestamp.utcnow()
    end_ms   = int(now.timestamp() * 1_000)
    start_ms = int((now - pd.Timedelta(days=days)).timestamp() * 1_000)

    data = _get("get_volatility_index_data", {
        "currency":        currency,
        "start_timestamp": start_ms,
        "end_timestamp":   end_ms,
        "resolution":      resolution,
    })

    # Each element: [timestamp_ms, open, high, low, close]
    rows = data["data"]
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    return df


def get_instruments(currency: str = DERIBIT_CURRENCY, kind: str = "option") -> pd.DataFrame:
    """Return all active instruments for *currency* of the given *kind*.

    Endpoint: ``GET /public/get_instruments``

    Args:
        currency: ``"BTC"`` or ``"ETH"``.
        kind:     ``"option"``, ``"future"``, or ``"spot"``.

    Returns:
        DataFrame with one row per instrument and columns from the Deribit API.
    """
    data = _get("get_instruments", {"currency": currency, "kind": kind, "expired": False})
    return pd.DataFrame(data)


def get_option_chain(currency: str = DERIBIT_CURRENCY) -> pd.DataFrame:
    """Return a snapshot of the full BTC/ETH option chain with Greeks.

    Iterates over active option instruments and fetches their current ticker
    data (bid, ask, mark price, IV, Greeks, open interest).

    Endpoint: ``GET /public/ticker``

    A 50 ms sleep is inserted between consecutive ticker requests to stay
    within Deribit's public rate limit (~20 requests/second sustainable).

    Args:
        currency: ``"BTC"`` or ``"ETH"``.

    Returns:
        DataFrame with one row per option contract.
    """
    instruments_df = get_instruments(currency, kind="option")
    rows = []
    for instrument_name in instruments_df["instrument_name"]:
        try:
            ticker = _get("ticker", {"instrument_name": instrument_name})
            rows.append({
                "instrument":   instrument_name,
                "bid":          ticker.get("best_bid_price"),
                "ask":          ticker.get("best_ask_price"),
                "mark_price":   ticker.get("mark_price"),
                "mark_iv":      ticker.get("mark_iv"),
                "delta":        ticker.get("greeks", {}).get("delta"),
                "gamma":        ticker.get("greeks", {}).get("gamma"),
                "vega":         ticker.get("greeks", {}).get("vega"),
                "theta":        ticker.get("greeks", {}).get("theta"),
                "open_interest": ticker.get("open_interest"),
            })
        except (requests.RequestException, KeyError, ValueError):
            # Skip instruments whose ticker cannot be fetched (e.g. expired or delisted)
            continue
        # Respect Deribit public rate limit: ~20 req/s → 50 ms between requests
        time.sleep(0.05)
    return pd.DataFrame(rows)
