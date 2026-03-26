# config/settings.py
# Central configuration for the trade-proof-system

# ── Exchange ──────────────────────────────────────────────────────────────────
DEFAULT_EXCHANGE    = "binance"
# Exchanges tried in order when the primary one is unavailable (e.g. geo-block).
EXCHANGE_FALLBACKS  = ["binance", "kraken", "bybit", "kucoin"]
DEFAULT_SYMBOL      = "BTC/USDT"
DEFAULT_TIMEFRAME = "1h"
DEFAULT_LIMIT    = 500          # Number of OHLCV candles to fetch

# ── Annualisation factor ───────────────────────────────────────────────────────
# Crypto trades 24 h / 7 days → 365 * 24 hours in a year
ANNUALISATION_FACTOR = 365 * 24  # hourly data

# ── Deribit (options data) ────────────────────────────────────────────────────
DERIBIT_BASE_URL = "https://www.deribit.com/api/v2"
DERIBIT_CURRENCY = "BTC"        # BTC or ETH

# ── Volatility ────────────────────────────────────────────────────────────────
RV_ROLLING_WINDOW = 24           # 24-candle rolling window for realised vol (≈ 24 h on 1 h data)
DASHBOARD_TITLE = "Mini Bloomberg Crypto"
DEFAULT_TARGET_PRICE_OFFSET = 0.05   # 5 % above current price as default
