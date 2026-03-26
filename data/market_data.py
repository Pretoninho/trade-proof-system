# data/market_data.py
# Fetch OHLCV (candlestick) data from a centralised exchange via ccxt.
#
# Primary source  : Binance via ccxt
#   Spot   klines : GET https://api.binance.com/api/v3/klines
#   Futures klines: GET https://fapi.binance.com/fapi/v1/klines
#
# Fallback source : CoinGecko public REST API (no API key required)
#   Endpoint      : GET https://api.coingecko.com/api/v3/coins/{coin}/market_chart
#   Note          : CoinGecko returns aggregated price data, not true OHLC candles.
#                   open/high/low are set equal to close; volume is 0.
#                   This is sufficient for volatility and directional analysis.
#
# Rate limits (Binance Spot public endpoints, per IP):
#   1 200 request-weight / minute.
#   Klines weight: 1 (limit < 100), 2 (100 ≤ limit < 500), 5 (limit ≥ 500).
#   Exceeding the limit returns HTTP 429; repeated violations → HTTP 418 ban.
#   Reference: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits
#
# ccxt handles rate-limit back-off automatically when enableRateLimit=True.

import math
import warnings

import ccxt
import requests
import pandas as pd

from config.settings import DEFAULT_EXCHANGE, DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, DEFAULT_LIMIT

# ── CoinGecko helpers ─────────────────────────────────────────────────────────

# Maps ccxt-style trading pairs to CoinGecko coin IDs.
_COINGECKO_COIN_MAP: dict[str, str] = {
    "BTC/USDT": "bitcoin",
    "ETH/USDT": "ethereum",
    "BNB/USDT": "binancecoin",
    "SOL/USDT": "solana",
    "XRP/USDT": "ripple",
}

_COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart"

# Approximate number of candles per calendar day for common timeframes.
_CANDLES_PER_DAY: dict[str, int] = {
    "1m": 1440, "3m": 480, "5m": 288, "15m": 96, "30m": 48,
    "1h": 24,   "2h": 12,  "4h": 6,   "6h": 4,   "8h": 3,
    "12h": 2,   "1d": 1,
}


def _limit_to_days(limit: int, timeframe: str) -> int:
    """Convert a candle *limit* + *timeframe* to a number of days for CoinGecko.

    CoinGecko granularity:
        ≤ 1 day  → minutely
        ≤ 90 days → hourly
        > 90 days → daily
    """
    if timeframe not in _CANDLES_PER_DAY:
        warnings.warn(
            f"Unknown timeframe '{timeframe}'; assuming 24 candles per day for CoinGecko day calculation.",
            stacklevel=3,
        )
    cpd = _CANDLES_PER_DAY.get(timeframe, 24)
    return max(1, math.ceil(limit / cpd))


def _get_coingecko_data(coin: str, days: int) -> pd.DataFrame:
    """Fetch price history from CoinGecko and return a tidy OHLCV DataFrame.

    Because CoinGecko's ``market_chart`` endpoint provides only a single price
    series (not true OHLC bars), ``open``, ``high``, and ``low`` are set equal
    to ``close`` and ``volume`` is set to ``0``.  This is sufficient for the
    realised-volatility and trend-direction calculations used by this system.

    Args:
        coin: CoinGecko coin ID (e.g. ``"bitcoin"``).
        days: Number of calendar days of history to retrieve.

    Returns:
        DataFrame indexed by ``timestamp`` with columns:
        ``open``, ``high``, ``low``, ``close``, ``volume``.

    Raises:
        requests.HTTPError: When the CoinGecko API returns a non-2xx response.
    """
    url = _COINGECKO_URL.format(coin=coin)
    params: dict[str, str | int] = {"vs_currency": "usd", "days": days}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise requests.RequestException(
            f"CoinGecko fallback failed for coin='{coin}', days={days}: {exc}"
        ) from exc

    prices = response.json()["prices"]  # [[timestamp_ms, price], ...]
    df = pd.DataFrame(prices, columns=["timestamp", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["open"]   = df["close"]
    df["high"]   = df["close"]
    df["low"]    = df["close"]
    df["volume"] = 0.0
    df.set_index("timestamp", inplace=True)
    return df[["open", "high", "low", "close", "volume"]]


# ── Public API ────────────────────────────────────────────────────────────────

def get_exchange(exchange_id: str = DEFAULT_EXCHANGE) -> ccxt.Exchange:
    """Return an initialised ccxt exchange instance with rate limiting enabled."""
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def get_ohlcv(
    symbol: str = DEFAULT_SYMBOL,
    timeframe: str = DEFAULT_TIMEFRAME,
    limit: int = DEFAULT_LIMIT,
    exchange_id: str = DEFAULT_EXCHANGE,
) -> pd.DataFrame:
    """Fetch OHLCV candles and return a tidy DataFrame.

    Tries the primary exchange (Binance via ccxt) first.  If the request fails
    for any reason (network error, geo-block, rate-limit ban, …) the function
    automatically falls back to the CoinGecko public API so the rest of the
    pipeline continues without interruption.

    Primary path (ccxt / Binance):
        ``GET /api/v3/klines`` (Spot) or ``GET /fapi/v1/klines`` (Futures).

    Fallback path (CoinGecko):
        ``GET /api/v3/coins/{coin}/market_chart``
        ``open``, ``high``, ``low`` equal ``close``; ``volume`` is ``0``.

    Args:
        symbol:      Trading pair in ccxt format, e.g. ``"BTC/USDT"``.
        timeframe:   Candle interval, e.g. ``"1m"``, ``"1h"``, ``"4h"``, ``"1d"``.
        limit:       Number of candles to retrieve (max 1 500 for Binance).
        exchange_id: ccxt exchange identifier (default: ``"binance"``).

    Returns:
        DataFrame indexed by ``timestamp`` with columns:
        ``open``, ``high``, ``low``, ``close``, ``volume``.
    """
    try:
        exchange = get_exchange(exchange_id)
        raw = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
    except ccxt.BaseError:
        coin = _COINGECKO_COIN_MAP.get(symbol)
        if coin is None:
            warnings.warn(
                f"Symbol '{symbol}' is not in _COINGECKO_COIN_MAP; "
                "falling back to 'bitcoin'. Data may not match the requested pair.",
                stacklevel=2,
            )
            coin = "bitcoin"
        days = _limit_to_days(limit, timeframe)
        return _get_coingecko_data(coin, days)
