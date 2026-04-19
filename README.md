# Kraken Adaptive Trading Bot

A Kraken crypto trading research bot. The live loop is deliberately simple;
the important work happens in the backtester before a strategy is trusted.

## Current Strategy

- Long only
- Trade only when the 50 EMA is above the 200 EMA
- Enter on a 20 EMA pullback with a bullish close, local high breakout, and volume confirmation
- Exit with a configurable ATR stop or swing-low stop and reward/risk target
- Backtests include a configurable fee rate

## Setup

```bash
python3 -m pip install -r requirements.txt
cp .env.example.txt .env
```

## Download Candles

Binance may return HTTP 451 from restricted locations. The downloader now tries
US-accessible fallback exchanges and USD/USDC quote pairs automatically, so the
examples below work even when `SOL/USDT` is not available on the selected venue.

```bash
python3 scripts/download_ohlcv.py --exchange binance --symbol SOL/USDT --timeframe 5m --days 365 --output data/sol_5m_365d.csv
python3 scripts/download_ohlcv.py --exchange binance --symbol BTC/USDT --timeframe 1h --days 365 --output data/btc_1h_365d.csv
python3 scripts/download_ohlcv.py --exchange binance --symbol ETH/USDT --timeframe 1h --days 365 --output data/eth_1h_365d.csv
```

## Backtest

```bash
python3 backtest/backtest.py data/btc_1h_365d.csv --starting-balance 1000 --risk-pct 0.01 --fee-rate 0.0026
```

Do not deploy live money until the strategy has been tested across multiple
assets and market regimes with acceptable profit factor, drawdown, and
expectancy after fees.

The backtester caps position size to available cash by default. To test smaller
cash exposure, lower `--max-position-pct`; for example `--max-position-pct 0.25`.

Useful research flags:

```bash
python3 backtest/backtest.py data/sol_ohlcv.csv --diagnostics
python3 backtest/backtest.py data/sol_ohlcv.csv --pullback-tolerance-pct 0.002 --reward-risk 3 --diagnostics
python3 backtest/backtest.py data/sol_ohlcv.csv --pullback-tolerance-pct 0.003 --no-prior-high-reclaim --volume-multiplier 0.8 --diagnostics
python3 backtest/backtest.py data/sol_ohlcv.csv --pullback-lookback-bars 6 --pullback-tolerance-pct 0.003 --reward-risk 3 --volume-multiplier 0.8 --diagnostics
python3 backtest/backtest.py data/sol_ohlcv.csv --breakout-lookback-bars 8 --diagnostics
python3 backtest/backtest.py data/sol_ohlcv.csv --stop-mode swing-low --swing-lookback-bars 6 --swing-stop-buffer-atr 0.25 --diagnostics
```
