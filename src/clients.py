import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream

load_dotenv()

@dataclass(frozen=True)
class Settings:
    key_id: str
    secret_key: str
    paper: bool = True  # we default to paper trading

    @staticmethod
    def from_env() -> "Settings":
        key = os.getenv("APCA_API_KEY_ID")
        sec = os.getenv("APCA_API_SECRET_KEY")
        if not key or not sec:
            raise RuntimeError("Missing APCA_API_KEY_ID/APCA_API_SECRET_KEY in .env")
        return Settings(key, sec, True)

_settings: Optional[Settings] = None
_trading_client: Optional[TradingClient] = None
_data_client: Optional[StockHistoricalDataClient] = None
_stream: Optional[StockDataStream] = None

def settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings

def trading_client() -> TradingClient:
    global _trading_client
    if _trading_client is None:
        s = settings()
        # paper=True ensures paper endpoint is used
        _trading_client = TradingClient(api_key=s.key_id, secret_key=s.secret_key, paper=s.paper)
    return _trading_client

def data_client() -> StockHistoricalDataClient:
    global _data_client
    if _data_client is None:
        s = settings()
        _data_client = StockHistoricalDataClient(api_key=s.key_id, secret_key=s.secret_key)
    return _data_client

def data_stream() -> StockDataStream:
    global _stream
    if _stream is None:
        s = settings()
        _stream = StockDataStream(api_key=s.key_id, secret_key=s.secret_key)
    return _stream