# Kraken Adaptive Trading Bot

A Kraken crypto trading research bot. The live loop is deliberately simple;
the important work happens in the backtester before a strategy is trusted.

## Current Strategy

- Long only
- Trade only when the 50 EMA is above the 200 EMA
- Enter on a 20 EMA pullback with a bullish close, prior-high reclaim, and volume confirmation
- Exit with a 1 ATR stop or 2 ATR target
- Backtests include a configurable fee rate

## Setup

```bash
python3 -m pip install -r requirements.txt
cp .env.example.txt .env
```

## Download Candles

```bash
python3 scripts/download_ohlcv.py --symbol SOL/USD --timeframe 5m --days 180 --output data/sol_ohlcv.csv
```

## Backtest

```bash
python3 backtest/backtest.py data/sol_ohlcv.csv --starting-balance 1000 --risk-pct 0.01 --fee-rate 0.0026
```

Do not deploy live money until the strategy has been tested across multiple
assets and market regimes with acceptable profit factor, drawdown, and
expectancy after fees.
