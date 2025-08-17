#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.strategies.pairs import PairsStrategy
from src.data_api import get_bars
from datetime import datetime, timedelta
import pandas as pd

def backtest_strategy():
    """Backtest the strategy with historical data"""
    print("🧪 Backtesting Pairs Strategy...")
    
    # Strategy parameters
    stock1, stock2 = "AAPL", "MSFT"
    lookback_days = 30
    entry_threshold = 1.5
    exit_threshold = 0.5
    initial_capital = 10000
    
    # Create strategy
    strategy = PairsStrategy(stock1, stock2, lookback_days)
    strategy.entry_threshold = entry_threshold
    strategy.exit_threshold = exit_threshold
    
    # Get historical data (last 6 months)
    end_date = datetime.now() - timedelta(days=2)  # Last trading day
    start_date = end_date - timedelta(days=500)
    
    print(f"📊 Getting data from {start_date.date()} to {end_date.date()}")
    
    bars1 = get_bars([stock1], "1D", start_date, end_date)
    bars2 = get_bars([stock2], "1D", start_date, end_date)
    
    if bars1.empty or bars2.empty:
        print("❌ No data available")
        return
    
    # Extract prices
    prices1 = bars1.xs(stock1)['close']
    prices2 = bars2.xs(stock2)['close']
    prices1, prices2 = prices1.align(prices2, join='inner')
    
    print(f"✅ Got {len(prices1)} trading days")
    
    # Calculate spread
    spread = strategy.calculate_spread(prices1, prices2)
    
    # Backtest variables
    capital = initial_capital
    position = 0
    entry_spread = None
    entry_date = None
    trades = []
    
    print(f"\n💰 Starting capital: ${capital:,.2f}")
    print("🔄 Running backtest...\n")
    
    # Run strategy day by day
    for i in range(lookback_days, len(spread)):
        current_date = spread.index[i]
        current_spread = spread.iloc[i]
        current_price1 = prices1.iloc[i]
        current_price2 = prices2.iloc[i]
        
        # Get historical spread for this day
        historical_spread = spread.iloc[i-lookback_days:i]
        mean_spread = historical_spread.mean()
        std_spread = historical_spread.std()
        
        if std_spread == 0:
            continue
            
        z_score = (current_spread - mean_spread) / std_spread
        
        # Check for entry signal
        if position == 0:  # No position
            if z_score > entry_threshold:
                # Short stock1, long stock2
                position = -1
                entry_spread = current_spread
                entry_date = current_date
                entry_capital = capital
                
                # Calculate position size
                position_value = capital * 0.02
                shares1 = int(position_value / current_price1)
                shares2 = int(position_value / current_price2)
                
                print(f"🎯 ENTRY: {current_date.date()} - SHORT {stock1}, LONG {stock2}")
                print(f"   Spread: {current_spread:.4f}, Z-score: {z_score:.2f}")
                print(f"   {stock1}: {shares1} shares @ ${current_price1:.2f}")
                print(f"   {stock2}: {shares2} shares @ ${current_price2:.2f}")
                
        # Check for exit signal
        elif position != 0:  # Have position
            exit_z_score = abs(z_score)
            if exit_z_score < exit_threshold:
                # Calculate profit/loss
                if position == -1:  # Short stock1, long stock2
                    # Simplified P&L calculation
                    pnl = (entry_spread - current_spread) / entry_spread * entry_capital * 0.02
                else:
                    pnl = (current_spread - entry_spread) / entry_spread * entry_capital * 0.02
                
                capital += pnl
                
                print(f"🚪 EXIT: {current_date.date()} - Spread: {current_spread:.4f}")
                print(f"   P&L: ${pnl:+.2f}, New Capital: ${capital:,.2f}")
                print(f"   Hold period: {(current_date - entry_date).days} days")
                print()
                
                # Log trade
                trades.append({
                    'entry_date': entry_date.date(),
                    'exit_date': current_date.date(),
                    'position': position,
                    'entry_spread': entry_spread,
                    'exit_spread': current_spread,
                    'pnl': pnl,
                    'hold_days': (current_date - entry_date).days
                })
                
                # Reset position
                position = 0
                entry_spread = None
                entry_date = None
    
    # Final results
    print("=" * 50)
    print("📊 BACKTEST RESULTS")
    print("=" * 50)
    print(f"💰 Final capital: ${capital:,.2f}")
    print(f"📈 Total return: ${capital - initial_capital:+,.2f}")
    print(f"📊 Return %: {((capital / initial_capital) - 1) * 100:+.2f}%")
    print(f"🔄 Total trades: {len(trades)}")
    
    if trades:
        profitable_trades = len([t for t in trades if t['pnl'] > 0])
        win_rate = profitable_trades / len(trades) * 100
        avg_pnl = sum(t['pnl'] for t in trades) / len(trades)
        avg_hold = sum(t['hold_days'] for t in trades) / len(trades)
        
        print(f"✅ Profitable trades: {profitable_trades}/{len(trades)}")
        print(f"🎯 Win rate: {win_rate:.1f}%")
        print(f"💰 Average P&L per trade: ${avg_pnl:+.2f}")
        print(f"⏰ Average hold period: {avg_hold:.1f} days")
        
        # Show individual trades
        print(f"\n📋 Trade Details:")
        for i, trade in enumerate(trades, 1):
            print(f"   Trade {i}: {trade['entry_date']} → {trade['exit_date']} | P&L: ${trade['pnl']:+.2f}")

if __name__ == "__main__":
    backtest_strategy()
