def position_size(balance_usd, risk_pct=0.02):
    return balance_usd * risk_pct


def stop_loss(entry_price, pct=0.025):
    return entry_price * (1 - pct)


def take_profit(entry_price, pct=0.05):
    return entry_price * (1 + pct)