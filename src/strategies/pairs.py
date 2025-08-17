import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from datetime import datetime

class PairsStrategy:
    def __init__(self, stock1: str, stock2: str, lookback_days: int = 30):
        self.stock1 = stock1.upper()
        self.stock2 = stock2.upper()
        self.lookback_days = lookback_days
        self.position = 0  # -1: short stock1/long stock2, 0: neutral, 1: long stock1/short stock2
        self.entry_spread = None
        self.entry_time = None
        
        # Risk management
        self.max_position_size = 0.05  # Max 5% of account per trade
        self.risk_per_trade = 0.02     # 2% of account per trade
        self.entry_threshold = 1.5     # Z-score threshold for entry
        self.exit_threshold = 0.5      # Z-score threshold for exit
    
    def calculate_spread(self, prices1: pd.Series, prices2: pd.Series) -> pd.Series:
        """Calculate the price spread between two stocks"""
        return prices1 / prices2
    
    def find_entry_signal(self, spread: pd.Series) -> Optional[int]:
        """Find entry signals based on z-score of spread"""
        if len(spread) < self.lookback_days:
            return None
            
        current_spread = spread.iloc[-1]
        historical_spread = spread.iloc[-self.lookback_days:-1]
        
        mean_spread = historical_spread.mean()
        std_spread = historical_spread.std()
        
        if std_spread == 0:
            return None
            
        z_score = (current_spread - mean_spread) / std_spread
        
        # Entry signals
        if z_score > self.entry_threshold:
            return -1  # Short stock1, long stock2
        elif z_score < -self.entry_threshold:
            return 1   # Long stock1, short stock2
            
        return None
    
    def find_exit_signal(self, spread: pd.Series) -> bool:
        """Find exit signal when spread returns to normal"""
        if len(spread) < self.lookback_days:
            return False
            
        current_spread = spread.iloc[-1]
        historical_spread = spread.iloc[-self.lookback_days:-1]
        
        mean_spread = historical_spread.mean()
        std_spread = historical_spread.std()
        
        if std_spread == 0:
            return False
            
        z_score = abs((current_spread - mean_spread) / std_spread)
        return z_score < self.exit_threshold
    
    def calculate_trade_details(self, signal: int, account_value: float, 
                              price1: float, price2: float) -> Dict:
        """Calculate all trade details: shares, orders, etc."""
        if signal == 0:
            return None
            
        # Calculate position size
        position_value = min(
            account_value * self.risk_per_trade,
            account_value * self.max_position_size
        )
        
        # Split equally between both stocks for balanced pairs trading
        dollars_per_stock = position_value / 2
        
        # Calculate shares
        shares1 = int(dollars_per_stock / price1)
        shares2 = int(dollars_per_stock / price2)
        
        if signal == 1:  # Long stock1, short stock2
            orders = [
                {"symbol": self.stock1, "side": "buy", "qty": shares1, "price": price1},
                {"symbol": self.stock2, "side": "sell", "qty": shares2, "price": price2}
            ]
        else:  # signal == -1: Short stock1, long stock2
            orders = [
                {"symbol": self.stock1, "side": "sell", "qty": shares1, "price": price1},
                {"symbol": self.stock2, "side": "buy", "qty": shares2, "price": price2}
            ]
        
        return {
            "signal": signal,
            "orders": orders,
            "position_value": position_value,
            "shares1": shares1,
            "shares2": shares2,
            "price1": price1,
            "price2": price2
        }
    
    def should_stop_loss(self, current_spread: float) -> bool:
        """Check if stop loss should trigger"""
        if self.position == 0 or self.entry_spread is None:
            return False
        
        # Calculate loss percentage
        if self.position == 1:  # Long stock1, short stock2
            loss_pct = (self.entry_spread - current_spread) / self.entry_spread
        else:  # Short stock1, long stock2
            loss_pct = (current_spread - self.entry_spread) / self.entry_spread
        
        return loss_pct > 0.02  # 2% stop loss
    
    def update_position(self, new_position: int, entry_spread: float = None):
        """Update strategy position and entry details"""
        self.position = new_position
        if entry_spread is not None:
            self.entry_spread = entry_spread
            self.entry_time = datetime.now()