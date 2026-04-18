def position_size(balance_usd, risk_pct=0.02):
    return balance_usd * risk_pct


def stop_loss(entry_price, pct=0.025):
    return entry_price * (1 - pct)


def take_profit(entry_price, pct=0.05):
    return entry_price * (1 + pct)


def units_for_fixed_risk(
    balance_usd,
    entry_price,
    stop_price,
    risk_pct=0.01,
    max_position_pct=1.0,
):
    risk_dollars = balance_usd * risk_pct
    risk_per_unit = abs(entry_price - stop_price)

    if risk_per_unit <= 0 or entry_price <= 0:
        return 0

    risk_units = risk_dollars / risk_per_unit
    cash_capped_units = (balance_usd * max_position_pct) / entry_price

    return min(risk_units, cash_capped_units)
