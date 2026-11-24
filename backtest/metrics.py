def summarize_trades(trades, starting_balance):
    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "net_pnl": 0,
            "ending_balance": starting_balance,
            "return_pct": 0,
            "profit_factor": 0,
            "max_drawdown_pct": 0,
            "expectancy": 0,
        }

    pnls = [trade["pnl"] for trade in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    equity = starting_balance
    peak = starting_balance
    max_drawdown_pct = 0

    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak:
            drawdown_pct = (peak - equity) / peak
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades),
        "net_pnl": sum(pnls),
        "ending_balance": starting_balance + sum(pnls),
        "return_pct": sum(pnls) / starting_balance if starting_balance else 0,
        "profit_factor": gross_win / gross_loss if gross_loss else float("inf"),
        "max_drawdown_pct": max_drawdown_pct,
        "expectancy": sum(pnls) / len(trades),
    }
