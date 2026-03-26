# data/market_data.py
# Fetch OHLCV (candlestick) data from a centralised exchange via ccxt.

import ccxt
import pandas as pd

from config.settings import DEFAULT_EXCHANGE, DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, DEFAULT_LIMIT


def get_exchange(exchange_id: str = DEFAULT_EXCHANGE) -> ccxt.Exchange:
    """Return an initialised ccxt exchange instance."""
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class()


def get_ohlcv(
    symbol: str = DEFAULT_SYMBOL,
    timeframe: str = DEFAULT_TIMEFRAME,
    limit: int = DEFAULT_LIMIT,
    exchange_id: str = DEFAULT_EXCHANGE,
) -> pd.DataFrame:
    """Fetch OHLCV candles and return a tidy DataFrame.

    Args:
        symbol:      Trading pair, e.g. ``"BTC/USDT"``.
        timeframe:   Candle interval, e.g. ``"1h"``, ``"4h"``, ``"1d"``.
        limit:       Number of candles to retrieve.
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
