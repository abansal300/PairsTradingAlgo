#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.strategies.pairs import PairsStrategy
from src.strategies.pairs_runner import PairsRunner

async def test_complete_strategy():
    """Test the complete strategy with trading execution"""
    print("�� Testing Complete Pairs Strategy...")
    
    # Use AAPL vs MSFT since we know it has a signal
    strategy = PairsStrategy("AAPL", "MSFT", lookback_days=30)
    runner = PairsRunner(strategy, check_interval=60)
    
    print("⏰ Running for 2 iterations...")
    
    for i in range(2):
        print(f"\n🔄 Iteration {i+1}/2")
        await runner.run_once()
        
        if i < 1:
            print("⏳ Waiting 1 minute...")
            await asyncio.sleep(60)
    
    print(f"\n📊 Final position: {strategy.position}")
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_complete_strategy())
