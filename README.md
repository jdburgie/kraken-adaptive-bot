# Kraken Adaptive Trading Bot

A modular crypto trading bot for Kraken using an RSI + volatility strategy.

## Features
- Kraken spot exchange integration via `ccxt`
- Adaptive buy/sell/hold signals based on momentum and volatility
- Simple risk helper functions for position sizing and stop/take levels
- Local script entrypoint for development

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your Kraken API credentials.

## Run locally

```bash
./scripts/run_local.sh
```

Or:

```bash
python -m bots.main
```

## Notes
- This project currently logs signals and does **not** place live orders (order lines are commented).
- Ensure you understand Kraken fees, slippage, and risk before enabling live execution.
