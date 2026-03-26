# data/market_data.py
# Fetch OHLCV (candlestick) data from a centralised exchange via ccxt.
#
# Binance public REST endpoints used (abstracted by ccxt):
#   Spot   klines : GET https://api.binance.com/api/v3/klines
#   Futures klines: GET https://fapi.binance.com/fapi/v1/klines
#
# Parameters:
#   symbol    — e.g. "BTCUSDT"
#   interval  — e.g. "1m", "5m", "15m", "1h", "4h", "1d"
#   limit     — max 1 500 candles per request (default 500)
#
# Rate limits (Binance Spot public endpoints, per IP):
#   1 200 request-weight / minute.
#   Klines weight: 1 (limit < 100), 2 (100 ≤ limit < 500), 5 (limit ≥ 500).
#   Exceeding the limit returns HTTP 429; repeated violations → HTTP 418 ban.
#   Reference: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits
#
# ccxt handles rate-limit back-off automatically when enableRateLimit=True.

import ccxt
import pandas as pd

from config.settings import DEFAULT_EXCHANGE, DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, DEFAULT_LIMIT


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

    Delegates to the ccxt ``fetch_ohlcv`` method which maps to:
    ``GET /api/v3/klines`` (Binance Spot) or
    ``GET /fapi/v1/klines`` (Binance Futures).

    Args:
        symbol:      Trading pair in ccxt format, e.g. ``"BTC/USDT"``.
        timeframe:   Candle interval, e.g. ``"1m"``, ``"1h"``, ``"4h"``, ``"1d"``.
        limit:       Number of candles to retrieve (max 1 500 for Binance).
        exchange_id: ccxt exchange identifier (default: ``"binance"``).

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume.
    """
    exchange = get_exchange(exchange_id)
    raw = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df
