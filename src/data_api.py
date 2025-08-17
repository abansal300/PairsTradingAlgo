from __future__ import annotations
import sys
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

import pandas as pd

from alpaca.data.requests import (
    StockBarsRequest,
    StockLatestQuoteRequest,
    StockLatestTradeRequest,
    StockSnapshotRequest,
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from .clients import data_client

# -------- Timeframe helpers --------

def parse_timeframe(s: str) -> TimeFrame:
    s = s.strip()
    if s.endswith("Min"):
        n = int(s[:-3])
        return TimeFrame(n, TimeFrameUnit.Minute)
    if s.endswith("H"):
        n = int(s[:-1])
        return TimeFrame(n, TimeFrameUnit.Hour)
    if s.endswith("D"):
        n = int(s[:-1])
        return TimeFrame(n, TimeFrameUnit.Day)
    # common aliases
    aliases = {
        "1m": TimeFrame(1, TimeFrameUnit.Minute),
        "5m": TimeFrame(5, TimeFrameUnit.Minute),
        "15m": TimeFrame(15, TimeFrameUnit.Minute),
        "30m": TimeFrame(30, TimeFrameUnit.Minute),
        "1h": TimeFrame(1, TimeFrameUnit.Hour),
        "1d": TimeFrame(1, TimeFrameUnit.Day),
    }
    key = s.lower()
    if key in aliases:
        return aliases[key]
    raise ValueError(f"Unrecognized timeframe '{s}'. Try 1Min, 5Min, 30Min, 1H, 1D, etc.")

# -------- Historical bars --------

def get_bars(symbols: Iterable[str], timeframe: str, start: Optional[datetime] = None, end: Optional[datetime] = None, limit: Optional[int] = None) -> pd.DataFrame:
    client = data_client()
    tf = parse_timeframe(timeframe)
    if end is None:
        end = datetime.now(timezone.utc)
    if start is None:
        # default: last 7 days
        start = end - timedelta(days=7)
    req = StockBarsRequest(
        symbol_or_symbols=[s.upper() for s in symbols],
        timeframe=tf,
        start=start,
        end=end,
        limit=limit,
    )
    resp = client.get_stock_bars(req)
    return resp.df  # MultiIndex [symbol, timestamp]

# -------- Latest quote/trade --------

def latest(symbol: str) -> dict:
    client = data_client()
    q = client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=symbol.upper()))
    t = client.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=symbol.upper()))
    return {
        "quote": q[symbol.upper()],
        "trade": t[symbol.upper()],
    }

# -------- Snapshots --------

def snapshots(symbols: Iterable[str]):
    client = data_client()
    snaps = client.get_stock_snapshots(StockSnapshotRequest(symbol_or_symbols=[s.upper() for s in symbols]))
    return snaps

# -------- Convenience: save bars to CSV --------

def save_bars_csv(symbol: str, timeframe: str, days: int, csv_path: str) -> str:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    df = get_bars([symbol], timeframe=timeframe, start=start, end=end)
    # For single symbol, drop the first level of MultiIndex for cleanliness
    if isinstance(df.index, pd.MultiIndex):
        try:
            df = df.xs(symbol.upper())
        except Exception:
            pass
    df.to_csv(csv_path)
    return csv_path