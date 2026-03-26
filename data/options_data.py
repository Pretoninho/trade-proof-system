# data/options_data.py
# Fetch options / volatility data from the Deribit public REST API.
#
# Deribit exposes a free, unauthenticated REST API for market data:
#   https://www.deribit.com/api/v2/public/<method>

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

    Args:
        currency: ``"BTC"`` or ``"ETH"``.

    Returns:
        DVOL value as a float (annualised %).
    """
    data = _get("get_volatility_index_data", {
        "currency": currency,
        "start_timestamp": 0,
        "end_timestamp": 9_999_999_999_999,
        "resolution": "1D",
    })
    # The API returns a list of [timestamp, open, high, low, close] arrays.
    # We return the most-recent close value.
    return float(data["data"][-1][4])


def get_instruments(currency: str = DERIBIT_CURRENCY, kind: str = "option") -> pd.DataFrame:
    """Return all active instruments for *currency* of the given *kind*.

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
    return pd.DataFrame(rows)
