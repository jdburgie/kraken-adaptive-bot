#!/usr/bin/env bash
set -euo pipefail

# Run with defaults (BTC/USD, 5m, 365 days, $1000 starting balance)
python -m bots.backtest "$@"
