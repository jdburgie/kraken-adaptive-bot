# Kraken Adaptive Trading Bot

A modular crypto trading bot for Kraken using an RSI + volatility strategy.

## Features
- Kraken spot exchange integration via `ccxt`
- Adaptive buy/sell/hold signals based on momentum and volatility
- Configurable `DRY_RUN` mode for safe local testing (default: enabled)
- Local script entrypoint for development

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your Kraken API credentials and trading settings.

## Run locally

```bash
./scripts/run_local.sh
```

Or:

```bash
python -m bots.main
```

## Run tests

```bash
python -m unittest discover -s tests
```

## Notes
- With `DRY_RUN=true`, the bot logs signals and order intents without placing live orders.
- Set `DRY_RUN=false` only after validating your strategy and risk controls.
- Ensure you understand Kraken fees, slippage, and risk before enabling live execution.
