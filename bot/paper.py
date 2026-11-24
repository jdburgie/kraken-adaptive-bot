try:
    from bot.trade_logger import log_trade
except ImportError:
    from trade_logger import log_trade

class PaperTrader:
    def __init__(self, starting_balance=100):
        self.balance = starting_balance
        self.position = None
        self.trade_history = []

    def buy(self, symbol, price, usd_amount, stop=None, target=None):
        if self.position is not None:
            return "Already in position"

        amount = usd_amount / price

        self.position = {
            "symbol": symbol,
            "entry_price": price,
            "amount": amount,
            "stop": stop,
            "target": target,
        }

        self.balance -= usd_amount

        return f"BOUGHT {amount:.6f} at {price}"

    def sell(self, symbol, price):
        if self.position is None:
            return "No position to sell"

        entry = self.position["entry_price"]
        amount = self.position["amount"]

        value = amount * price
        pnl = value - (amount * entry)

        self.balance += value

        trade = {
            "symbol": symbol,
            "entry": entry,
            "exit": price,
            "amount": amount,
            "pnl": pnl,
            "stop": self.position.get("stop"),
            "target": self.position.get("target"),
        }

        log_trade(trade)

        self.trade_history.append(trade)
        self.position = None

        return f"SOLD at {price} | PnL: {pnl:.2f}"

    def status(self):
        return {
            "balance": self.balance,
            "position": self.position,
            "trades": len(self.trade_history)
        }
