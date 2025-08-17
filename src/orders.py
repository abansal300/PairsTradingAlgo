from decimal import Decimal
from typing import Optional, List

from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, QueryOrderStatus
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
    GetOrdersRequest,
)

from .clients import trading_client

# -------- Account & positions --------

def account_summary() -> dict:
    tc = trading_client()
    acct = tc.get_account()
    return {
        "status": acct.status,
        "buying_power": str(acct.buying_power),
        "cash": str(acct.cash),
        "equity": str(acct.equity),
        "multiplier": acct.multiplier,
    }

def list_positions() -> List[dict]:
    tc = trading_client()
    poss = tc.get_all_positions()
    return [
        {
            "symbol": p.symbol,
            "qty": str(p.qty),
            "avg_entry": str(p.avg_entry_price),
            "market_value": str(p.market_value),
            "unrealized_pl": str(p.unrealized_pl),
        }
        for p in poss
    ]

# -------- Orders --------

def place_market_order(symbol: str, side: str, qty: Optional[Decimal] = None, notional: Optional[Decimal] = None, tif: str = "day"):
    if (qty is None) == (notional is None):
        raise ValueError("Provide exactly one of qty or notional for market order.")
    tc = trading_client()
    order = MarketOrderRequest(
        symbol=symbol.upper(),
        side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY if tif.lower() == "day" else TimeInForce.GTC,
        qty=str(qty) if qty is not None else None,
        notional=str(notional) if notional is not None else None,
    )
    return tc.submit_order(order_data=order)

def place_limit_order(symbol: str, side: str, qty: Decimal, limit_price: Decimal, tif: str = "day"):
    tc = trading_client()
    order = LimitOrderRequest(
        symbol=symbol.upper(),
        side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY if tif.lower() == "day" else TimeInForce.GTC,
        limit_price=str(limit_price),
        qty=str(qty),
    )
    return tc.submit_order(order_data=order)

def place_bracket_order(symbol: str, side: str, qty: Decimal, take_profit: Decimal, stop_loss: Decimal, stop_loss_limit: Optional[Decimal] = None, tif: str = "gtc"):
    tc = trading_client()
    order = MarketOrderRequest(
        symbol=symbol.upper(),
        side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY if tif.lower() == "day" else TimeInForce.GTC,
        qty=str(qty),
        order_class=OrderClass.BRACKET,
        take_profit=TakeProfitRequest(limit_price=str(take_profit)),
        stop_loss=StopLossRequest(stop_price=str(stop_loss), limit_price=str(stop_loss_limit) if stop_loss_limit else None),
    )
    return tc.submit_order(order_data=order)

def get_order(order_id: str):
    return trading_client().get_order_by_id(order_id)

def list_open_orders(limit: int = 50):
    tc = trading_client()
    filt = GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=limit)
    return tc.get_orders(filter=filt)

def cancel_order(order_id: str):
    trading_client().cancel_order_by_id(order_id)
    return {"cancelled": order_id}

def cancel_all_orders():
    return trading_client().cancel_orders()