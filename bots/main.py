import time

import pandas as pd

from bots.config import (
    CANDLE_LIMIT,
    DRY_RUN,
    RISK_PCT,
    STOP_LOSS_PCT,
    SYMBOL,
    TAKE_PROFIT_PCT,
    TIMEFRAME,
)
from bots.exchange import get_exchange
from bots.logger import logger
from bots.risk import stop_loss, take_profit
from bots.strategy import generate_signal


def fetch_data(exchange, limit=CANDLE_LIMIT):
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=limit)
    return pd.DataFrame(
        ohlcv,
        columns=["time", "open", "high", "low", "close", "volume"],
    )


def get_base_asset(symbol):
    return symbol.split("/")[0]


def get_balance_usd(exchange):
    if DRY_RUN:
        return 1000.0  # simulated balance in dry run
    balance = exchange.fetch_balance()
    return float(balance.get("USD", {}).get("free", 0))


def open_position(exchange, price, balance_usd):
    """Calculate size, place buy order, return position dict."""
    from bots.risk import position_size
    trade_usd = position_size(balance_usd, risk_pct=RISK_PCT)
    amount = trade_usd / price
    stop = stop_loss(price, pct=STOP_LOSS_PCT)
    take = take_profit(price, pct=TAKE_PROFIT_PCT)

    logger.info(
        f"BUY {SYMBOL} | price={price:.4f} | amount={amount:.6f} "
        f"| stop={stop:.4f} | take={take:.4f} | usd={trade_usd:.2f}"
    )

    if not DRY_RUN:
        exchange.create_market_buy_order(SYMBOL, amount)

    return {
        "active": True,
        "entry_price": price,
        "amount": amount,
        "stop_price": stop,
        "take_price": take,
    }


def close_position(exchange, position, price, reason):
    """Place sell order and clear position."""
    amount = position["amount"]
    entry = position["entry_price"]
    pnl = (price - entry) / entry * 100

    logger.info(
        f"SELL {SYMBOL} | reason={reason} | price={price:.4f} "
        f"| entry={entry:.4f} | pnl={pnl:+.2f}%"
    )

    if not DRY_RUN:
        base = get_base_asset(SYMBOL)
        balance = exchange.fetch_balance()
        live_amount = float(balance.get(base, {}).get("free", 0))
        if live_amount > 0:
            exchange.create_market_sell_order(SYMBOL, live_amount)
        else:
            logger.warning(f"SELL skipped — no {base} balance found")

    return {"active": False, "entry_price": None, "amount": None,
            "stop_price": None, "take_price": None}


def run_bot(poll_interval=60):
    exchange = get_exchange()
    logger.info(f"Starting bot | pair={SYMBOL} | timeframe={TIMEFRAME} | dry_run={DRY_RUN}")

    position = {"active": False, "entry_price": None, "amount": None,
                "stop_price": None, "take_price": None}

    while True:
        try:
            df = fetch_data(exchange)
            price = df["close"].iloc[-1]

            # --- Position management: check stop/take before signal ---
            if position["active"]:
                if price <= position["stop_price"]:
                    position = close_position(exchange, position, price, "STOP_LOSS")
                elif price >= position["take_price"]:
                    position = close_position(exchange, position, price, "TAKE_PROFIT")
                else:
                    signal = generate_signal(df)
                    logger.info(
                        f"Signal={signal} | Price={price:.4f} "
                        f"| Stop={position['stop_price']:.4f} "
                        f"| Take={position['take_price']:.4f}"
                    )
                    if signal == "SELL":
                        position = close_position(exchange, position, price, "SIGNAL")

            # --- No position: look for entry ---
            else:
                signal = generate_signal(df)
                logger.info(f"Signal={signal} | Price={price:.4f} | No open position")

                if signal == "BUY":
                    balance_usd = get_balance_usd(exchange)
                    if balance_usd > 10:
                        position = open_position(exchange, price, balance_usd)
                    else:
                        logger.warning(f"BUY signal but insufficient USD balance: {balance_usd:.2f}")

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as exc:
            logger.error(f"Error: {exc}", exc_info=True)
            time.sleep(10)


if __name__ == "__main__":
    run_bot()
