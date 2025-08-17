#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.strategies.pairs import PairsStrategy
from src.data_api import get_bars
from datetime import datetime, timedelta

def test_historical_signals():
    """Test strategy with historical data to see what signals it would have generated"""
    print("📊 Testing Strategy with Historical Data...")
    
    # Test with data from last week
    end_date = datetime.now() - timedelta(days=2)  # Last Thursday
    start_date = end_date - timedelta(days=60)
    
    strategy = PairsStrategy("AAPL", "MSFT", lookback_days=30)
    
    # Get historical data
    bars1 = get_bars(["AAPL"], "1D", start_date, end_date)
    bars2 = get_bars(["MSFT"], "1D", start_date, end_date)
    
    if bars1.empty or bars2.empty:
        print("❌ No historical data available")
        return
    
    # Extract prices
    prices1 = bars1.xs("AAPL")['close']
    prices2 = bars2.xs("MSFT")['close']
    prices1, prices2 = prices1.align(prices2, join='inner')
    
    print(f"✅ Got {len(prices1)} trading days")
    
    # Calculate spread for each day
    spread = strategy.calculate_spread(prices1, prices2)
    
    # Check for signals over time
    signals_found = 0
    for i in range(30, len(spread)):
        historical_spread = spread.iloc[i-30:i]
        current_spread = spread.iloc[i]
        date = spread.index[i]
        
        # Calculate z-score
        mean_spread = historical_spread.mean()
        std_spread = historical_spread.std()
        
        if std_spread > 0:
            z_score = (current_spread - mean_spread) / std_spread
            
            # Check for entry signals
            if abs(z_score) > 1.5:
                signal_type = "LONG AAPL/SHORT MSFT" if z_score < -1.5 else "SHORT AAPL/LONG MSFT"
                print(f"🎯 Signal on {date.date()}: {signal_type} (Z-score: {z_score:.2f})")
                signals_found += 1
    
    print(f"\n📊 Total signals found: {signals_found}")
    print(f"📈 Current spread: {spread.iloc[-1]:.4f}")

if __name__ == "__main__":
    test_historical_signals()
