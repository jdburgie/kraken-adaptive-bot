"""
Risk management helpers.

position_size_usd: returns the dollar amount to deploy so that if
the stop loss is hit, we lose exactly risk_pct * balance.

Example:
  balance   = $1,000
  risk_pct  = 0.01  (risk 1% of account = $10)
  stop_pct  = 0.025 (stop is 2.5% below entry)
  → position_usd = $10 / 0.025 = $400
  → if price drops 2.5%, loss = $400 * 0.025 = $10 ✓
"""


def position_size_usd(balance: float, risk_pct: float, stop_pct: float) -> float:
    """Dollar amount to commit to trade."""
    if stop_pct <= 0:
        raise ValueError("stop_pct must be positive")
    return (balance * risk_pct) / stop_pct


def stop_loss_price(entry_price: float, pct: float) -> float:
    return entry_price * (1 - pct)


def take_profit_price(entry_price: float, pct: float) -> float:
    return entry_price * (1 + pct)


def update_trailing_stop(current_stop: float, price: float, trail_pct: float) -> float:
    """Ratchet trailing stop up — never moves down."""
    new_stop = price * (1 - trail_pct)
    return max(current_stop, new_stop)
