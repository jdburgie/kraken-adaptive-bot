# Kraken Adaptive Bot

Automated BTC/USD trading bot using a hybrid mean-reversion + trend-following strategy.

## Strategy

**Entry** — all three conditions must be true:
1. **Strong uptrend**: price above EMA200 AND EMA50 above EMA200
2. **Oversold dip**: candle low touches or breaks below the lower Bollinger Band
3. **RSI oversold**: RSI(14) below 42

**Exit** — first condition hit wins:
1. **Trailing stop**: starts at 2.5% below entry, ratchets up as price rises
2. **Take profit**: 9% above entry
3. **RSI exit**: RSI(14) above 65

## Backtest Results (BTC/USD 1h, Apr 2024 – Apr 2026)

| Metric | Value |
|---|---|
| Return | **+24.8%** |
| BTC buy-and-hold | +19.9% |
| Trades | 89 |
| Win rate | 39.3% |
| Avg win | +3.91% |
| Avg loss | -1.93% |
| Profit factor | 1.26 |
| Max drawdown | -17.2% |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add your Kraken API keys
```

## Run Backtest

```bash
# Default: BTC/USD, 730 days, $1000 balance, 1% risk
./scripts/run_backtest.sh

# Custom
python -m bots.backtest --symbol ETH/USD --days 365 --balance 500 --risk 0.02
```

## Run Bot (dry run by default)

```bash
./scripts/run_local.sh
# or
python -m bots.main
```

Set `DRY_RUN=false` in `.env` only after reviewing backtest output.

## Risk Settings

| Variable | Default | Meaning |
|---|---|---|
| `RISK_PCT` | `0.01` | 1% of balance AT RISK per trade |
| `STOP_PCT` | `0.025` | Trailing stop 2.5% below price |
| `TAKE_PCT` | `0.09` | Take profit 9% above entry |

Position size is auto-calculated so a stop loss hit = exactly `RISK_PCT` loss.

## Tests

```bash
python -m unittest discover -s tests
```

---
**Risk warning**: Crypto trading involves significant financial risk. Always backtest before going live. Never trade more than you can afford to lose.
