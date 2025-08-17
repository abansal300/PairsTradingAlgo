#!/usr/bin/env python3
import asyncio
from src.strategies.pairs import PairsStrategy
from src.strategies.pairs_runner import PairsRunner

async def run_pairs_strategy():
    # Create strategy for Apple vs Microsoft
    strategy = PairsStrategy("AAPL", "MSFT", lookback_days=30)
    
    # Create and run the automated trader
    runner = PairsRunner(strategy, check_interval=300)  # Check every 5 minutes
    
    try:
        await runner.run_forever()
    except KeyboardInterrupt:
        print("Stopping strategy...")
        runner.stop()

if __name__ == "__main__":
    asyncio.run(run_pairs_strategy())
