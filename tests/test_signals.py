#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.strategies.pairs import PairsStrategy
from src.data_api import get_bars
from datetime import datetime, timedelta

def test_signal_generation():
    """Test if the strategy can generate entry/exit signals"""
    print("🧪 Testing Pairs Strategy Signal Generation...")
    
    # Test different stock pairs
    test_pairs = [
        ("AAPL", "MSFT"),
        ("GOOGL", "META"), 
        ("TSLA", "NVDA"),
        ("AMZN", "NFLX")
    ]
    
    for stock1, stock2 in test_pairs:
        print(f"\n📊 Testing {stock1} vs {stock2}")
        
        try:
            # Create strategy
            strategy = PairsStrategy(stock1, stock2, lookback_days=30)
            
            # Get historical data
            end_time = datetime.now()
            start_time = end_time - timedelta(days=60)  # Get more data
            
            bars1 = get_bars([stock1], "1D", start_time, end_time)
            bars2 = get_bars([stock2], "1D", start_time, end_time)
            
            if bars1.empty or bars2.empty:
                print(f"   ❌ No data for {stock1} or {stock2}")
                continue
            
            # Extract prices
            prices1 = bars1.xs(stock1)['close']
            prices2 = bars2.xs(stock2)['close']
            prices1, prices2 = prices1.align(prices2, join='inner')
            
            print(f"   ✅ Got {len(prices1)} trading days")
            
            # Calculate spread
            spread = strategy.calculate_spread(prices1, prices2)
            current_spread = spread.iloc[-1]
            
            print(f"   📈 Current spread: {current_spread:.4f}")
            print(f"   📈 Spread range: {spread.min():.4f} - {spread.max():.4f}")
            
            # Test different thresholds
            thresholds = [1.5, 2.0, 2.5]
            for threshold in thresholds:
                entry_signal = strategy.find_entry_signal(spread, threshold)
                exit_signal = strategy.find_exit_signal(spread, threshold/3)
                
                signal_text = "None"
                if entry_signal == 1:
                    signal_text = f"Long {stock1}/Short {stock2}"
                elif entry_signal == -1:
                    signal_text = f"Short {stock1}/Long {stock2}"
                
                print(f"   🎯 Threshold {threshold}: Entry={signal_text}, Exit={exit_signal}")
            
            # Check if current spread is extreme
            historical_spread = spread.iloc[-30:-1]
            mean_spread = historical_spread.mean()
            std_spread = historical_spread.std()
            
            if std_spread > 0:
                z_score = abs((current_spread - mean_spread) / std_spread)
                print(f"   📊 Z-score: {z_score:.2f}")
                
                if z_score > 2.0:
                    print(f"   �� EXTREME SPREAD DETECTED!")
                elif z_score > 1.5:
                    print(f"   ⚠️  Moderate deviation")
                else:
                    print(f"   ✅ Normal spread")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_signal_generation()
