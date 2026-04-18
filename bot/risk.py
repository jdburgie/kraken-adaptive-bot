def position_size(balance_usd, risk_pct=0.02):
    return balance_usd * risk_pct


def stop_loss(entry_price, pct=0.025):
    return entry_price * (1 - pct)


def take_profit(entry_price, pct=0.05):
    return entry_price * (1 + pct)


def units_for_fixed_risk(balance_usd, entry_price, stop_price, risk_pct=0.01):
    risk_dollars = balance_usd * risk_pct
    risk_per_unit = abs(entry_price - stop_price)

    if risk_per_unit <= 0:
        return 0

    return risk_dollars / risk_per_unit
