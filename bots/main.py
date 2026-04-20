"""
Live bot entry point.

Runs the hybrid strategy on a configurable polling interval.
Manages position state including trailing stop in memory.
All order logic is gated behind DRY_RUN so the bot is safe by default.
"""

import time

import pandas as pd

from bots.config import (
    CANDLE_LIMIT, DRY_RUN, RISK_PCT, STOP_PCT, SYMBOL, TAKE_PCT, TIMEFRAME,
)
from bots.exchange import get_exchange
from bots.logger import logger
from bots.risk import (
    position_size_usd,
    stop_loss_price,
    take_profit_price,
    update_trailing_stop,
)
from bots.strategy import generate_signal, MIN_CANDLES


# ── Data ─────────────────────────────────────────────────────────────────────

def fetch_data(exchange, limit: int = CANDLE_LIMIT) -> pd.DataFrame:
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=limit)
    return pd.DataFrame(
        ohlcv, columns=["time", "open", "high", "low", "close", "volume"]
    )


def get_usd_balance(exchange) -> float:
    if DRY_RUN:
        return 1_000.0
    balance = exchange.fetch_balance()
    return float(balance.get("USD", {}).get("free", 0.0))


def get_base_asset(symbol: str) -> str:
    return symbol.split("/")[0]


# ── Trade execution ───────────────────────────────────────────────────────────

def open_position(exchange, price: float, balance_usd: float) -> dict:
    trade_usd = position_size_usd(balance_usd, RISK_PCT, STOP_PCT)
    amount    = trade_usd / price
    stop      = stop_loss_price(price, STOP_PCT)
    take      = take_profit_price(price, TAKE_PCT)

    logger.info(
        f"BUY  {SYMBOL} | price=${price:,.2f} | "
        f"size=${trade_usd:,.2f} ({amount:.6f}) | "
        f"stop=${stop:,.2f} | take=${take:,.2f}"
    )

    if not DRY_RUN:
        exchange.create_market_buy_order(SYMBOL, amount)

    return {
        "active":        True,
        "entry_price":   price,
        "amount":        amount,
        "stop_price":    stop,
        "take_price":    take,
        "trail_stop":    stop,   # trailing stop starts at initial stop
    }


def close_position(exchange, position: dict, price: float, reason: str) -> dict:
    entry  = position["entry_price"]
    amount = position["amount"]
    pnl    = (price - entry) / entry * 100

    logger.info(
        f"SELL {SYMBOL} | reason={reason} | "
        f"price=${price:,.2f} | entry=${entry:,.2f} | pnl={pnl:+.2f}%"
    )

    if not DRY_RUN:
        base  = get_base_asset(SYMBOL)
        bal   = exchange.fetch_balance()
        live  = float(bal.get(base, {}).get("free", 0.0))
        if live > 0:
            exchange.create_market_sell_order(SYMBOL, live)
        else:
            logger.warning(f"SELL skipped — no {base} balance found")

    return {
        "active": False, "entry_price": None, "amount": None,
        "stop_price": None, "take_price": None, "trail_stop": None,
    }


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_bot(poll_interval: int = 3600):  # default 1h to match TIMEFRAME
    exchange = get_exchange()
    logger.info(
        f"Bot starting | pair={SYMBOL} | tf={TIMEFRAME} | "
        f"dry_run={DRY_RUN} | risk={RISK_PCT*100:.1f}% | "
        f"stop={STOP_PCT*100:.1f}% | take={TAKE_PCT*100:.1f}%"
    )

    position = {
        "active": False, "entry_price": None, "amount": None,
        "stop_price": None, "take_price": None, "trail_stop": None,
    }

    while True:
        try:
            df    = fetch_data(exchange)
            price = float(df["close"].iloc[-1])

            # ── Manage open position ─────────────────────────────────────────
            if position["active"]:

                # Ratchet trailing stop up
                position["trail_stop"] = update_trailing_stop(
                    position["trail_stop"], price, STOP_PCT
                )

                logger.info(
                    f"Position open | price=${price:,.2f} | "
                    f"entry=${position['entry_price']:,.2f} | "
                    f"trail_stop=${position['trail_stop']:,.2f} | "
                    f"take=${position['take_price']:,.2f}"
                )

                if price <= position["trail_stop"]:
                    position = close_position(exchange, position, price, "TRAIL_STOP")

                elif price >= position["take_price"]:
                    position = close_position(exchange, position, price, "TAKE_PROFIT")

                else:
                    signal = generate_signal(df)
                    if signal == "SELL":
                        position = close_position(exchange, position, price, "RSI_EXIT")

            # ── Look for entry ───────────────────────────────────────────────
            else:
                signal = generate_signal(df)
                logger.info(f"No position | signal={signal} | price=${price:,.2f}")

                if signal == "BUY":
                    balance = get_usd_balance(exchange)
                    if balance >= 10.0:
                        position = open_position(exchange, price, balance)
                    else:
                        logger.warning(f"BUY signal ignored — low balance: ${balance:.2f}")

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as exc:
            logger.error(f"Unhandled error: {exc}", exc_info=True)
            time.sleep(30)


if __name__ == "__main__":
    run_bot()
