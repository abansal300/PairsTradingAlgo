import argparse
from decimal import Decimal
from typing import List

from .orders import (
    account_summary,
    list_positions,
    place_market_order,
    place_limit_order,
    place_bracket_order,
    get_order,
    list_open_orders,
    cancel_order,
    cancel_all_orders,
)
from .data_api import get_bars, latest, snapshots, save_bars_csv

# Optional: streaming (bars/quotes/trades)
from .clients import data_stream
from alpaca.data.models import Bar, Quote, Trade


def main():
    p = argparse.ArgumentParser(description="alpaca-py paper trading helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("account")
    sub.add_parser("positions")

    # Market orders
    buy = sub.add_parser("buy"); buy.add_argument("symbol");
    mx = buy.add_mutually_exclusive_group(required=True)
    mx.add_argument("--qty", type=Decimal)
    mx.add_argument("--notional", type=Decimal)
    buy.add_argument("--tif", default="day", choices=["day","gtc","opg","cls","ioc","fok"])

    sell = sub.add_parser("sell"); sell.add_argument("symbol");
    mxs = sell.add_mutually_exclusive_group(required=True)
    mxs.add_argument("--qty", type=Decimal)
    mxs.add_argument("--notional", type=Decimal)
    sell.add_argument("--tif", default="day", choices=["day","gtc","opg","cls","ioc","fok"])

    # Limit orders
    bl = sub.add_parser("buy-limit"); bl.add_argument("symbol"); bl.add_argument("--qty", type=Decimal, required=True); bl.add_argument("--limit", type=Decimal, required=True); bl.add_argument("--tif", default="day", choices=["day","gtc"])
    sl = sub.add_parser("sell-limit"); sl.add_argument("symbol"); sl.add_argument("--qty", type=Decimal, required=True); sl.add_argument("--limit", type=Decimal, required=True); sl.add_argument("--tif", default="day", choices=["day","gtc"])

    # Bracket
    br = sub.add_parser("buy-bracket")
    br.add_argument("symbol"); br.add_argument("--qty", type=Decimal, required=True)
    br.add_argument("--tp", type=Decimal, required=True, help="take-profit limit price")
    br.add_argument("--sl", type=Decimal, required=True, help="stop-loss stop price")
    br.add_argument("--sl-limit", type=Decimal, help="optional stop-loss limit price (stop-limit)")
    br.add_argument("--tif", default="gtc", choices=["day","gtc"])

    # Orders mgmt
    sub.add_parser("orders")
    go = sub.add_parser("order"); go.add_argument("order_id")
    co = sub.add_parser("cancel"); co.add_argument("order_id")
    sub.add_parser("cancel-all")

    # Data: bars / latest / snapshots
    bars = sub.add_parser("bars")
    bars.add_argument("symbol")
    bars.add_argument("--timeframe", default="1Min")
    bars.add_argument("--days", type=int, default=5)
    bars.add_argument("--csv")

    lat = sub.add_parser("latest"); lat.add_argument("symbol")
    sn = sub.add_parser("snapshots"); sn.add_argument("symbols", nargs="+")

    # Streaming
    st = sub.add_parser("stream")
    st.add_argument("symbol")
    st.add_argument("--channels", nargs="+", default=["bars"], choices=["bars","quotes","trades"])

    args = p.parse_args()

    if args.cmd == "account":
        print(account_summary()); return
    if args.cmd == "positions":
        for row in list_positions():
            print(row)
        return

    if args.cmd == "buy":
        o = place_market_order(args.symbol, side="buy", qty=args.qty, notional=args.notional, tif=args.tif); print(o); return
    if args.cmd == "sell":
        o = place_market_order(args.symbol, side="sell", qty=args.qty, notional=args.notional, tif=args.tif); print(o); return

    if args.cmd == "buy-limit":
        o = place_limit_order(args.symbol, side="buy", qty=args.qty, limit_price=args.limit, tif=args.tif); print(o); return
    if args.cmd == "sell-limit":
        o = place_limit_order(args.symbol, side="sell", qty=args.qty, limit_price=args.limit, tif=args.tif); print(o); return

    if args.cmd == "buy-bracket":
        o = place_bracket_order(args.symbol, side="buy", qty=args.qty, take_profit=args.tp, stop_loss=args.sl, stop_loss_limit=args.sl_limit, tif=args.tif); print(o); return

    if args.cmd == "orders":
        for o in list_open_orders():
            print(o)
        return
    if args.cmd == "order":
        print(get_order(args.order_id)); return
    if args.cmd == "cancel":
        print(cancel_order(args.order_id)); return
    if args.cmd == "cancel-all":
        print(cancel_all_orders()); return

    if args.cmd == "bars":
        if args.csv:
            path = save_bars_csv(args.symbol, args.timeframe, args.days, args.csv)
            print(f"Saved bars to {path}")
        else:
            df = get_bars([args.symbol], timeframe=args.timeframe)
            print(df.head(20))
        return

    if args.cmd == "latest":
        print(latest(args.symbol)); return

    if args.cmd == "snapshots":
        print(snapshots(args.symbols)); return

    if args.cmd == "stream":
        stream = data_stream()

        async def on_bar(b: Bar):
            print("BAR", b.symbol, b.close, b.timestamp)
        async def on_quote(q: Quote):
            print("QUOTE", q.symbol, q.ask_price, q.bid_price, q.timestamp)
        async def on_trade(t: Trade):
            print("TRADE", t.symbol, t.price, t.size, t.timestamp)

        if "bars" in args.channels:
            stream.subscribe_bars(on_bar, args.symbol.upper())
        if "quotes" in args.channels:
            stream.subscribe_quotes(on_quote, args.symbol.upper())
        if "trades" in args.channels:
            stream.subscribe_trades(on_trade, args.symbol.upper())

        import asyncio
        try:
            asyncio.run(stream.run())
        except KeyboardInterrupt:
            pass