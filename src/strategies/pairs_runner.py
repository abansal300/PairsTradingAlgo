import asyncio
from datetime import datetime, timedelta
from typing import Optional

from .pairs import PairsStrategy
from ..data_api import get_bars
from ..orders import place_market_order, list_positions
from ..clients import trading_client

class PairsRunner:
    def __init__(self, strategy: PairsStrategy, check_interval: int = 300):
        self.strategy = strategy
        self.check_interval = check_interval
        self.running = False
        self.trade_history = []
        
    async def run_once(self):
        """Run one iteration of the strategy"""
        try:
            # Get market data
            end_time = datetime.now()
            calendar_days_needed = int(self.strategy.lookback_days * 1.5)
            start_time = end_time - timedelta(days=calendar_days_needed)
            
            print(f"📊 Getting {calendar_days_needed} calendar days of data...")
            
            bars1 = get_bars([self.strategy.stock1], "1D", start_time, end_time)
            bars2 = get_bars([self.strategy.stock2], "1D", start_time, end_time)
            
            if bars1.empty or bars2.empty:
                print(f"❌ No data for {self.strategy.stock1} or {self.strategy.stock2}")
                return
            
            # Extract prices
            prices1 = bars1.xs(self.strategy.stock1)['close']
            prices2 = bars2.xs(self.strategy.stock2)['close']
            prices1, prices2 = prices1.align(prices2, join='inner')
            
            if len(prices1) < self.strategy.lookback_days:
                print(f"❌ Not enough data: {len(prices1)} days")
                return
            
            print(f"✅ Got {len(prices1)} trading days")
            
            # Strategy does all the math
            spread = self.strategy.calculate_spread(prices1, prices2)
            entry_signal = self.strategy.find_entry_signal(spread)
            exit_signal = self.strategy.find_exit_signal(spread)
            
            current_spread = spread.iloc[-1]
            print(f"📈 Current spread: {current_spread:.4f}")
            print(f"🎯 Entry signal: {entry_signal}, Exit signal: {exit_signal}")
            
            # Execute trades based on strategy signals
            if entry_signal and self.strategy.position == 0:
                await self._execute_entry(entry_signal, current_spread)
            elif exit_signal and self.strategy.position != 0:
                await self._execute_exit()
                
        except Exception as e:
            print(f"❌ Error in strategy execution: {e}")
    
    async def _execute_entry(self, signal: int, current_spread: float):
        """Execute entry trade based on strategy calculations"""
        try:
            print(f"🚀 EXECUTING TRADE: Signal {signal}")
            
            # Get account info
            tc = trading_client()
            account = tc.get_account()
            account_value = float(account.equity)
            
            # Get current prices
            latest1 = get_bars([self.strategy.stock1], "1D", limit=1)
            latest2 = get_bars([self.strategy.stock2], "1D", limit=1)
            
            price1 = float(latest1.xs(self.strategy.stock1)['close'].iloc[-1])
            price2 = float(latest2.xs(self.strategy.stock2)['close'].iloc[-1])
            
            # Strategy calculates all trade details
            trade_details = self.strategy.calculate_trade_details(signal, account_value, price1, price2)
            
            if not trade_details:
                print("❌ No trade details calculated")
                return
            
            print(f"📊 Position value: ${trade_details['position_value']:.2f}")
            print(f"📊 {self.strategy.stock1}: {trade_details['shares1']} shares at ${price1:.2f}")
            print(f"📊 {self.strategy.stock2}: {trade_details['shares2']} shares at ${price2:.2f}")
            
            # Execute orders
            for order in trade_details['orders']:
                if order['side'] == 'buy':
                    print(f"🟢 BUYING {order['symbol']}: {order['qty']} shares")
                    placed_order = place_market_order(order['symbol'], "buy", qty=order['qty'])
                    print(f"✅ Order placed: {placed_order}")
                else:  # sell
                    print(f"🔴 SELLING {order['symbol']}: {order['qty']} shares")
                    placed_order = place_market_order(order['symbol'], "sell", qty=order['qty'])
                    print(f"✅ Order placed: {placed_order}")
            
            # Update strategy position
            self.strategy.update_position(signal, current_spread)
            
            # Log trade
            self.trade_history.append({
                'timestamp': datetime.now(),
                'action': 'entry',
                'details': trade_details
            })
            
        except Exception as e:
            print(f"❌ Trade execution error: {e}")
    
    async def _execute_exit(self):
        """Execute exit trade"""
        try:
            print(f"🚪 Exiting position: {self.strategy.position}")
            
            # Close all positions
            positions = list_positions()
            for pos in positions:
                symbol = pos['symbol']
                qty = float(pos['qty'])
                if qty > 0:
                    print(f"🔴 SELLING {symbol}: {qty} shares")
                    place_market_order(symbol, "sell", qty=qty)
                # Note: For short positions, you'd buy to cover
            
            self.strategy.update_position(0)
            print("✅ Position closed")
            
            # Log trade
            self.trade_history.append({
                'timestamp': datetime.now(),
                'action': 'exit',
                'position': self.strategy.position
            })
            
        except Exception as e:
            print(f"❌ Exit execution error: {e}")
    
    async def run_forever(self):
        """Run the strategy continuously"""
        self.running = True
        print(f"🚀 Starting pairs strategy for {self.strategy.stock1}/{self.strategy.stock2}")
        
        while self.running:
            await self.run_once()
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the strategy"""
        self.running = False

    def print_performance_summary(self):
        """Print strategy performance"""
        if not self.trade_history:
            print("No trades executed yet")
            return
        
        total_trades = len(self.trade_history)
        profitable_trades = len([t for t in self.trade_history if t.get('pnl', 0) > 0])
        
        print(f"📊 Performance Summary:")
        print(f"   Total trades: {total_trades}")
        print(f"   Profitable: {profitable_trades}")
        print(f"   Win rate: {profitable_trades/total_trades*100:.1f}%")