# 📊 Trade Proof System — Mini Bloomberg Crypto Terminal

> A modular, open-source trading analytics platform that recreates ~70 % of a Bloomberg Terminal's core functionality using accessible tools — focused on **crypto volatility & options analysis**.

---

## 🎯 Vision

You don't need a $25 000/year Bloomberg subscription to trade options professionally.  
This project gives you:

- ✅ Real-time OHLCV data (via ccxt / Binance)
- ✅ Realised volatility analysis
- ✅ Price-move probability engine (Black-Scholes log-normal)
- ✅ Volatility & trend signal generation
- ✅ Deribit DVOL & options chain integration
- ✅ Interactive Streamlit dashboard

---

## 🧱 Architecture

```
trade-proof-system/
│
├── data/                  # Data retrieval (APIs)
│   ├── market_data.py     # OHLCV via ccxt (Binance, etc.)
│   └── options_data.py    # Deribit DVOL & option chain
│
├── analytics/             # Calculations (volatility, stats, signals)
│   ├── volatility.py      # Realised vol, expected move, rolling RV
│   └── signals.py         # Vol signal (IV vs RV), trend signal (SMA crossover)
│
├── models/                # Probabilistic models
│   └── probability.py     # P(price ≥ target), P(price in range)
│
├── dashboard/             # Streamlit UI
│   └── app.py             # Interactive Bloomberg-style terminal
│
├── config/
│   └── settings.py        # Centralised configuration
│
├── main.py                # CLI orchestrator
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the CLI orchestrator

```bash
python main.py
# or with custom parameters:
python main.py --symbol ETH/USDT --timeframe 4h --iv 75 --horizon 3
```

**CLI flags:**

| Flag          | Default     | Description                               |
|---------------|-------------|-------------------------------------------|
| `--symbol`    | `BTC/USDT`  | Trading pair                              |
| `--timeframe` | `1h`        | Candle interval                           |
| `--limit`     | `500`       | Number of candles to fetch                |
| `--iv`        | *(uses RV)* | Implied volatility in % (e.g. `70`)       |
| `--horizon`   | `1`         | Probability horizon in days               |

### 3. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📡 Modules

### `data/market_data.py`

Fetches OHLCV candlestick data from any exchange supported by [ccxt](https://github.com/ccxt/ccxt).

```python
from data.market_data import get_ohlcv

df = get_ohlcv(symbol="BTC/USDT", timeframe="1h", limit=500)
print(df.tail())
```

### `data/options_data.py`

Fetches volatility and options data from the **Deribit** public REST API (no API key required for market data).

```python
from data.options_data import get_dvol, get_option_chain

dvol = get_dvol("BTC")          # e.g. 65.2 (annualised %)
chain_df = get_option_chain("BTC")  # full option chain with Greeks
```

### `analytics/volatility.py`

Core volatility metrics.

```python
from analytics.volatility import realized_volatility, expected_move

vol = realized_volatility(df)                    # e.g. 0.65 (65 % annualised)
em  = expected_move(vol, price, horizon_days=1)  # ±$ move over 1 day
```

### `analytics/signals.py`

Trading signal generation.

```python
from analytics.signals import vol_signal, trend_signal

sig = vol_signal(realized_vol=0.55, implied_vol=0.70)  # "SELL VOL"
ts  = trend_signal(df)                                  # "BULLISH"
```

### `models/probability.py`

Probability engine based on the log-normal (Black-Scholes) distribution.

```python
from models.probability import probability_move, probability_range

# Probability BTC reaches $100 000 within 7 days
p = probability_move(current_price=95_000, target_price=100_000, vol=0.65, horizon_days=7)
print(f"{p:.2%}")  # e.g. 23.4%

# Probability BTC stays between $90k and $100k for 1 day
p_range = probability_range(95_000, 90_000, 100_000, 0.65, horizon_days=1)
```

---

## 🖥️ Dashboard

The Streamlit dashboard provides a Bloomberg-style interface:

| Panel                        | Description                                        |
|------------------------------|----------------------------------------------------|
| **Key Metrics**              | Live price, RV, IV, expected move                  |
| **Signals**                  | Vol signal (RV vs IV), SMA trend signal            |
| **Probability Calculator**   | Single-target & range probability inputs           |
| **Price Chart**              | Interactive close-price line chart                 |
| **Rolling Realised Vol**     | 24-candle rolling RV chart                         |
| **Raw OHLCV**                | Expandable last-50-candles data table              |

---

## 🔮 Roadmap

| Feature                            | Status      |
|------------------------------------|-------------|
| Real-time OHLCV (ccxt)             | ✅ Done     |
| Realised volatility                | ✅ Done     |
| Price-move probabilities           | ✅ Done     |
| Vol & trend signals                | ✅ Done     |
| Streamlit dashboard                | ✅ Done     |
| Deribit DVOL integration           | ✅ Done     |
| Full options chain with Greeks     | ✅ Done     |
| 25Δ Put/Call skew analysis         | 🔜 Planned |
| Event tracker (FOMC, CPI, halving) | 🔜 Planned |
| Automated backtesting engine       | 🔜 Planned |
| Machine learning (pattern detect.) | 🔜 Planned |

---

## 🛠️ Tech Stack

| Layer       | Tool               |
|-------------|--------------------|
| Data        | ccxt, requests     |
| Analytics   | numpy, scipy       |
| Data frames | pandas             |
| UI          | Streamlit          |
| Language    | Python 3.11+       |

---

## 📜 License

MIT — free to use, modify, and distribute.