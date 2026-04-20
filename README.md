# Kraken Adaptive Trading Bot

A modular crypto trading bot for Kraken using an RSI + EMA trend filter + volume confirmation strategy.

## Features
- Kraken spot exchange integration via `ccxt`
- **Trend filter**: only buys dips when price is above EMA50 (no buying into downtrends)
- **Volume confirmation**: only enters on candles with above-average volume
- **Stop loss + take profit**: automatically exits positions at configured levels
- **Position tracking**: survives restarts knowing whether it's in a trade
- **Backtesting engine**: walk-forward simulation against 1 year of real Kraken data
- Configurable `DRY_RUN` mode (default: enabled)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Kraken API keys and settings
```

## Backtest (run this before going live)

Test the strategy against the last 365 days of BTC/USD data:

```bash
./scripts/run_backtest.sh
```

Custom options:
```bash
# Test ETH/USD on 1h candles for the last 180 days with $500 starting balance
python -m bots.backtest --symbol ETH/USD --timeframe 1h --days 180 --balance 500
```

The backtest prints a full report and saves a chart image (`backtest_BTC-USD_5m_365d.png`).

## Run live (dry run by default)

```bash
./scripts/run_local.sh
```

Or:
```bash
python -m bots.main
```

With `DRY_RUN=true` (default), the bot logs signals without placing real orders.
Set `DRY_RUN=false` in `.env` only after reviewing backtest results.

## Run tests

```bash
python -m unittest discover -s tests
```

## Configuration (`.env`)

| Variable         | Default   | Description                                 |
|------------------|-----------|---------------------------------------------|
| `KRAKEN_API_KEY` | —         | Kraken API key                              |
| `KRAKEN_API_SECRET` | —      | Kraken API secret                           |
| `SYMBOL`         | `BTC/USD` | Trading pair                                |
| `TIMEFRAME`      | `5m`      | Candle interval                             |
| `DRY_RUN`        | `true`    | Paper trading mode                          |
| `RISK_PCT`       | `0.02`    | Fraction of balance to risk per trade (2%)  |
| `STOP_LOSS_PCT`  | `0.025`   | Stop loss below entry (2.5%)                |
| `TAKE_PROFIT_PCT`| `0.05`    | Take profit above entry (5%)                |
| `EMA_PERIOD`     | `50`      | EMA period for trend direction filter       |
| `CANDLE_LIMIT`   | `100`     | Candles fetched per live tick               |

## Risk warning
This bot is for educational purposes. Crypto trading involves significant financial risk.
Always backtest before going live. Never trade more than you can afford to lose.
