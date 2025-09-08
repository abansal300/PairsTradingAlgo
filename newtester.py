#!/usr/bin/env python3

import os
from alpaca_trade_api.stream import Stream


os.environ['ALPACA_API_KEY']    = 'PKZZEINJNV5FKHH0U4IS'
os.environ['ALPACA_SECRET_KEY'] = 'zNUNmlaMLaQYYJYLnNZO33CIWZGmB7d5HCY7iI8D'
API_KEY    = os.environ['ALPACA_API_KEY']
API_SECRET = os.environ['ALPACA_SECRET_KEY']

# Initialize the stream with SIP feed
stream = Stream(
    API_KEY,
    API_SECRET,
    base_url="https://paper-api.alpaca.markets",  # Use live URL if trading live
    data_feed='sip'  # Make sure you're on a premium plan for SIP
)


import types, sys

# ─── Stub out everything yfinance.live tries to import ────────────────────
# Top-level package
sys.modules['websockets'] = types.ModuleType('websockets')

# websockets.sync package
sys.modules['websockets.sync'] = types.ModuleType('websockets.sync')

# websockets.sync.client module with a dummy `connect`
sync_client = types.ModuleType('websockets.sync.client')
def sync_connect(*args, **kwargs):
    raise NotImplementedError("stub")
sync_client.connect = sync_connect
sys.modules['websockets.sync.client'] = sync_client

# websockets.asyncio package
sys.modules['websockets.asyncio'] = types.ModuleType('websockets.asyncio')

# websockets.asyncio.client module with a dummy `connect`
async_client = types.ModuleType('websockets.asyncio.client')
def async_connect(*args, **kwargs):
    raise NotImplementedError("stub")
async_client.connect = async_connect
sys.modules['websockets.asyncio.client'] = async_client

import yfinance as yf


import os
import time
import logging
import itertools
from datetime import datetime, time as dt_time
import pytz

import pandas as pd
from alpaca_trade_api.rest import REST

# ──────────────────────────────────────────────────────────────────────────────
# STRATEGY CLASS (from backtester)
# ──────────────────────────────────────────────────────────────────────────────
class RealTimeTradingStrategy:
    def __init__(
        self,
        api: REST,
        hedge_ratio: float,
        mean_train: float,
        std_train: float,
        entry_z: float = 1.0,
        exit_z: float = 0.9,
        slippage_pct: float = 0.0005,
        stop_loss_pct: float = 0.05,
        initial_capital: float = 1_000.0,
    ):
        self.api = api
        self.hedge_ratio = hedge_ratio
        self.mean_train = mean_train
        self.std_train = std_train
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.slippage_pct = slippage_pct
        self.capital = initial_capital
        self.stop_loss_pct = stop_loss_pct
        self.stop_price_y = None
        self.stop_price_x = None
        self.position = 0
        self.entry_price_y = 0
        self.entry_price_x = 0
        self.entry_time = None
        self.trade_log = []
        logging.info(f"Strategy initialized: entry_z={entry_z}, exit_z={exit_z}, capital={initial_capital}")

    def get_latest_prices(self, symbol: str) -> float:
        if self.api is None:
            logging.error("API not initialized—cannot fetch real-time prices.")
            return None
        try:
            trade = self.api.get_latest_trade(symbol, feed='sip')
            # some SDK versions expose price as .price, others as .p — keep both:
            price = getattr(trade, "price", None)
            if price is None:
                price = getattr(trade, "p", None)
            return price
        except Exception as e:
            logging.error(f"Error fetching price for {symbol}: {e}")
            return None

    def place_order(self, symbol: str, qty: int, side: str, type: str = "market", time_in_force: str = "gtc"):
        if self.api is None:
            logging.info(f"Simulated {side} {qty}@{symbol}")
            return True
        try:
            order = self.api.submit_order(
                symbol=symbol, qty=qty, side=side, type=type, time_in_force=time_in_force
            )
            logging.info(f"Order {side} {qty}@{symbol} → ID {order.id}")
            return order
        except Exception as e:
            logging.error(f"Order error {side} {symbol}: {e}")
            return None

    def process_data(
        self,
        y_symbol: str,
        x_symbol: str,
        date: datetime = None,
        y_price: float = None,
        x_price: float = None,
    ):
        action = "HOLD"
        trade_details = None
        zscore = None
        now = date or datetime.now()

        # 1) fetch or receive prices
        if y_price is None or x_price is None:
            if self.api is None:
                logging.error(f"{now}: No prices & no API.")
                return action, trade_details, self.capital, zscore
            y_price = self.get_latest_prices(y_symbol)
            x_price = self.get_latest_prices(x_symbol)

        # 2) validate

        # 2a) Make sure std_train is non‐zero
        if self.std_train == 0:
          logging.error(f"{now}: std_train=0, cannot compute z-score.")
          return action, trade_details, self.capital, zscore

        # 2b) Make sure we've got valid price scalars
        if y_price is None or x_price is None:
          logging.warning(f"{now}: missing price data.")
          return action, trade_details, self.capital, zscore

        # 2c) Guard against zero or negative prices
        if y_price <= 0 or x_price <= 0:
          logging.warning(f"{now}: non-positive price Y={y_price}, X={x_price}")
          return action, trade_details, self.capital, zscore


        # 3) compute z-score
        spread = y_price - self.hedge_ratio * x_price
        zscore = (spread - self.mean_train) / self.std_train

        # 4) update capital (real-time)
        if self.api:
            try:
                acct = self.api.get_account()
                self.capital = float(acct.equity)
            except Exception as e:
                logging.error(f"{now}: account fetch error: {e}")

        # ─── 4.5) STOP‑LOSS CHECK (live AND backtest) ───────────────────────────
        if self.position != 0:
            # LONG stop‑loss
            if self.position == 1 and (y_price <= self.stop_price_y or x_price >= self.stop_price_x):
                action = "STOP_LOSS_LONG"
            # SHORT stop‑loss
            elif self.position == -1 and (y_price >= self.stop_price_y or x_price <= self.stop_price_x):
                action = "STOP_LOSS_SHORT"
            else:
                action = None

            if action:
                # exit exactly like your normal exit code but tag it as STOP_LOSS
                exit_y = y_price * (1 + self.slippage_pct) if self.position==1 else y_price * (1 - self.slippage_pct)
                exit_x = x_price * (1 - self.slippage_pct) if self.position==1 else x_price * (1 + self.slippage_pct)
                pnl_y = (exit_y - self.entry_price_y) if self.position==1 else (self.entry_price_y - exit_y)
                pnl_x = (self.entry_price_x - exit_x) if self.position==1 else (exit_x - self.entry_price_x)
                gross = pnl_y - self.hedge_ratio * pnl_x if self.position==1 else pnl_y + self.hedge_ratio * pnl_x
                notional = abs(self.entry_price_y) + abs(self.hedge_ratio * self.entry_price_x)
                scaled = gross * (self.capital * 0.01 / notional if notional else 0)
                cap_before = self.capital
                self.capital += scaled

                trade_details = {
                    "Entry":    self.entry_time,
                    "Exit":     now,
                    "Dir":       "LONG" if self.position==1 else "SHORT",
                    "ExitType":  action,
                    "GrossPnL":  round(gross, 4),
                    "Scaled":    round(scaled, 2),
                    "CapBefore": round(cap_before, 2),
                    "CapAfter":  round(self.capital, 2),
                    "DurDays":   (now - self.entry_time).days,
                }
                self.trade_log.append(trade_details)
                self.position = 0
                logging.warning(f"{now}: {action} triggered at z={zscore:.2f}")
                return action, trade_details, self.capital, zscore

        # 5) ENTRY
        if self.position == 0:
            if zscore > self.entry_z:
                action = "SHORT"
                trade_amount = self.capital * 0.01
                qty_y = int(trade_amount / y_price / (1 + self.slippage_pct))
                qty_x = int(trade_amount / x_price / (1 - self.slippage_pct) * self.hedge_ratio)
                if qty_y and qty_x:
                    o1 = self.place_order(y_symbol, qty_y, "sell")
                    o2 = self.place_order(x_symbol, qty_x, "buy")
                    if o1 and o2:
                        self.position = -1
                        self.entry_time = now
                        self.entry_price_y, self.entry_price_x = y_price, x_price
                        # ← STOP‐LOSS levels for SHORT: lose if Y up  stop_loss_pct or X down stop_loss_pct
                        self.stop_price_y = self.entry_price_y * (1 + self.stop_loss_pct)  # ← stop‐loss
                        self.stop_price_x = self.entry_price_x * (1 - self.stop_loss_pct)  # ← stop‐loss
                        logging.info(f"{now}: ENTER SHORT z={zscore:.2f}")

            elif zscore < -self.entry_z:
                action = "LONG"
                trade_amount = self.capital * 0.01
                qty_y = int(trade_amount / y_price / (1 - self.slippage_pct))
                qty_x = int(trade_amount / x_price / (1 + self.slippage_pct) * self.hedge_ratio)
                if qty_y and qty_x:
                    o1 = self.place_order(y_symbol, qty_y, "buy")
                    o2 = self.place_order(x_symbol, qty_x, "sell")
                    if o1 and o2:
                        self.position = 1
                        self.entry_time = now
                        self.entry_price_y, self.entry_price_x = y_price, x_price
                        # ← STOP‐LOSS levels for LONG: lose if Y down  stop_loss_pct or X up stop_loss_pct
                        self.stop_price_y = self.entry_price_y * (1 - self.stop_loss_pct)  # ← stop‐loss
                        self.stop_price_x = self.entry_price_x * (1 + self.stop_loss_pct)  # ← stop‐loss
                        logging.info(f"{now}: ENTER LONG  z={zscore:.2f}")


        # 6) EXIT (live + backtest)
        elif self.position != 0:
            # fetch current share sizes from broker so we close the exact amounts we opened
            def _pos_qty(sym: str) -> int:
                try:
                    p = self.api.get_position(sym)
                    return abs(int(float(p.qty)))
                except Exception:
                    return 0  # no position or API error

            qty_y_open = _pos_qty(y_symbol)
            qty_x_open = _pos_qty(x_symbol)

            # compute exit + send orders for LONG (long Y, short X)
            if self.position == 1 and zscore > -self.exit_z:
                action = "CLOSE_LONG"

                # send opposite orders to flatten
                if qty_y_open > 0:
                    self.place_order(y_symbol, qty_y_open, "sell", time_in_force="day")
                if qty_x_open > 0:
                    self.place_order(x_symbol, qty_x_open, "buy",  time_in_force="day")

                # PnL calc (kept from your code)
                exit_y = y_price * (1 + self.slippage_pct)
                exit_x = x_price * (1 - self.slippage_pct)
                pnl_y = exit_y - self.entry_price_y
                pnl_x = self.entry_price_x - exit_x
                gross = pnl_y - self.hedge_ratio * pnl_x
                notional = abs(self.entry_price_y) + abs(self.hedge_ratio * self.entry_price_x)
                trade_amount = self.capital * 0.01
                scaled = gross * (trade_amount / notional if notional else 0)
                cap_before = self.capital
                self.capital += scaled
                trade_details = {
                    "Entry":    self.entry_time,
                    "Exit":     now,
                    "Dir":      "LONG",
                    "GrossPnL": round(gross, 4),
                    "Scaled":   round(scaled, 2),
                    "CapBefore":round(cap_before, 2),
                    "CapAfter": round(self.capital, 2),
                    "DurDays":  (now - self.entry_time).days,
                }
                self.trade_log.append(trade_details)
                self.position = 0
                logging.info(f"{now}: EXIT LONG  z={zscore:.2f} PnL={scaled:.2f}")

            # compute exit + send orders for SHORT (short Y, long X)
            elif self.position == -1 and zscore < self.exit_z:
                action = "CLOSE_SHORT"

                # send opposite orders to flatten
                if qty_y_open > 0:
                    self.place_order(y_symbol, qty_y_open, "buy",  time_in_force="day")
                if qty_x_open > 0:
                    self.place_order(x_symbol, qty_x_open, "sell", time_in_force="day")

                # PnL calc (kept from your code)
                exit_y = y_price * (1 - self.slippage_pct)
                exit_x = x_price * (1 + self.slippage_pct)
                pnl_y = self.entry_price_y - exit_y
                pnl_x = exit_x - self.entry_price_x
                gross = pnl_y + self.hedge_ratio * pnl_x
                notional = abs(self.entry_price_y) + abs(self.hedge_ratio * self.entry_price_x)
                trade_amount = self.capital * 0.01
                scaled = gross * (trade_amount / notional if notional else 0)
                cap_before = self.capital
                self.capital += scaled
                trade_details = {
                    "Entry":    self.entry_time,
                    "Exit":     now,
                    "Dir":      "SHORT",
                    "GrossPnL": round(gross, 4),
                    "Scaled":   round(scaled, 2),
                    "CapBefore":round(cap_before, 2),
                    "CapAfter": round(self.capital, 2),
                    "DurDays":  (now - self.entry_time).days,
                }
                self.trade_log.append(trade_details)
                self.position = 0
                logging.info(f"{now}: EXIT SHORT z={zscore:.2f} PnL={scaled:.2f}")

        return action, trade_details, self.capital, zscore


    def get_trade_log(self) -> pd.DataFrame:
        return pd.DataFrame(self.trade_log)

# ──────────────────────────────────────────────────────────────────────────────
# BACKTEST & OPTIMIZATION HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def run_backtest(
    StrategyClass,
    y_series: pd.Series,
    x_series: pd.Series,
    hedge_ratio, mean_train, std_train,
    entry_z, exit_z, slippage_pct, initial_capital
):
    strat = StrategyClass(
        api=None,
        hedge_ratio=hedge_ratio,
        mean_train=mean_train,
        std_train=std_train,
        entry_z=entry_z,
        exit_z=exit_z,
        slippage_pct=slippage_pct,
        initial_capital=initial_capital
    )
    for t in y_series.index:
        strat.process_data(None, None, date=t, y_price=y_series.loc[t], x_price=x_series.loc[t])
    total_return = (strat.capital - initial_capital) / initial_capital
    return {
        "entry_z": entry_z,
        "exit_z": exit_z,
        "return": total_return,
        "trades": len(strat.trade_log),
    }

def optimize_thresholds(
    StrategyClass, y_series, x_series,
    hedge_ratio, mean_train, std_train,
    slippage_pct, initial_capital,
    entry_grid, exit_grid
):
    results = []
    for e, x in itertools.product(entry_grid, exit_grid):
        if x >= e:
            continue
        stats = run_backtest(
            StrategyClass, y_series, x_series,
            hedge_ratio, mean_train, std_train,
            e, x, slippage_pct, initial_capital
        )
        results.append(stats)
    df = pd.DataFrame(results)
    return df.sort_values("return", ascending=False).reset_index(drop=True)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN: OPTIMIZE THEN RUN LIVE LOOP
# ──────────────────────────────────────────────────────────────────────────────
def main():
    print("Starting main function...")
    # -- ENV & LOGGING --
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("Logging configured...")
    # Use userdata.get for secure access to secrets
    API_KEY    = os.environ['ALPACA_API_KEY']
    API_SECRET = os.environ['ALPACA_SECRET_KEY']
    BASE_URL = "https://paper-api.alpaca.markets" # Use paper-api for testing
    api = REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')


    # -- SETTINGS --
    Y_SYMBOL      = "LLY"
    X_SYMBOL      = "AMGN"
    HEDGE_RATIO   = 5.105806
    SLIPPAGE_PCT  = 0.0005
    INITIAL_CAP   = 1_000.0
    ENTRY_GRID    = [0.5, 1.0, 1.5, 2.0]
    EXIT_GRID     = [0.25, 0.5, 0.75, 0.9]
    POLL_INTERVAL = 30  # seconds
    ET            = pytz.timezone("US/Eastern")
    MARKET_OPEN   = dt_time(9, 30)
    MARKET_CLOSE  = dt_time(16, 0)


    # ── FETCH HISTORICAL FOR OPTIMIZATION via yfinance ONLY ────────────────
    import yfinance as yf
    import pandas as pd

    logging.info("Downloading historical data from Yahoo Finance…")
    # download both at once (optional)
    df = yf.download([Y_SYMBOL, X_SYMBOL], period="2y", interval="1d")
    print("df.columns:", df.columns)

    # Pull out the two Close series from the MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        y_close = df[("Close", Y_SYMBOL)].copy()
        x_close = df[("Close", X_SYMBOL)].copy()
    else:
        # fallback if flat (unlikely here)
        y_close = df["Close"].copy()
        x_close = df["Close"].copy()  # not correct unless separate download

    # Now align on dates
    y_close, x_close = y_close.align(x_close, join="inner")
    print("After align – length:", len(y_close))
    if y_close.empty:
        raise RuntimeError("No overlapping dates after aligning close prices!")

    # Finally compute your spread stats
    spread     = y_close - HEDGE_RATIO * x_close
    mean_train = spread.mean()
    std_train  = spread.std()
    if std_train == 0 or pd.isna(std_train):
        raise RuntimeError(f"std_train is bad: {std_train}")

    logging.info(f"Training spread μ={mean_train:.4f}, σ={std_train:.4f}")


    # -- RUN GRID SEARCH --
    df_opt = optimize_thresholds(
        RealTimeTradingStrategy,
        y_close, x_close,
        HEDGE_RATIO, mean_train, std_train,
        SLIPPAGE_PCT, INITIAL_CAP,
        ENTRY_GRID, EXIT_GRID
    )
    best = df_opt.iloc[0]
    logging.info("Optimal thresholds → entry_z=%.2f, exit_z=%.2f, return=%.2f%%",
                 best.entry_z, best.exit_z, best["return"]*100)

    # -- START LIVE LOOP --
    strategy = RealTimeTradingStrategy(
        api=api,
        hedge_ratio=HEDGE_RATIO,
        mean_train=mean_train,
        std_train=std_train,
        entry_z=best.entry_z,
        exit_z=best.exit_z,
        slippage_pct=SLIPPAGE_PCT,
        initial_capital=INITIAL_CAP,
        stop_loss_pct=0.05,

    )
    logging.info("Entering live trading loop for %s/%s", Y_SYMBOL, X_SYMBOL)

    while True:
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        now_et  = now_utc.astimezone(ET)
        if now_et.weekday() < 5 and MARKET_OPEN <= now_et.time() <= MARKET_CLOSE:
            try:
                action, details, cap, z = strategy.process_data(Y_SYMBOL, X_SYMBOL)
                if details:
                    logging.info("Trade detail: %s", details)
            except Exception as e:
                logging.error("Loop error: %s", e)
        else:
            logging.info("Market closed (%s). Sleeping...", now_et.time())
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    print("Script starting...")
    try:
        main()
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()