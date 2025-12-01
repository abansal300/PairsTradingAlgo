#!/usr/bin/env python3

import os
from alpaca_trade_api.rest import REST

# Set credentials
os.environ['ALPACA_API_KEY'] = 'PKNTA2P3AB8DC3ZGQ6MP'
os.environ['ALPACA_SECRET_KEY'] = 'm3ugII9UkjFtTaUrIeqweO9c8uheaRYxpddaUEEK'

API_KEY = os.environ['ALPACA_API_KEY']
API_SECRET = os.environ['ALPACA_SECRET_KEY']
BASE_URL = 'https://paper-api.alpaca.markets'

print("Testing Alpaca API credentials...")

try:
    # Test basic API connection
    api = REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
    account = api.get_account()
    print(f"✅ API credentials work!")
    print(f"Account status: {account.status}")
    print(f"Account equity: ${account.equity}")
    print(f"Buying power: ${account.buying_power}")
    
    # Test free data feed (no SIP)
    print("\nTesting free data feed...")
    try:
        trade = api.get_latest_trade('AAPL', feed='iex')  # Free feed
        print(f"✅ Free data feed works! AAPL price: ${trade.price}")
    except Exception as e:
        print(f"❌ Free data feed error: {e}")
    
    # Test SIP data feed (premium)
    print("\nTesting SIP data feed...")
    try:
        trade = api.get_latest_trade('AAPL', feed='sip')  # Premium feed
        print(f"✅ SIP data feed works! AAPL price: ${trade.price}")
    except Exception as e:
        print(f"❌ SIP data feed error: {e}")
        print("This is expected if you don't have a premium subscription")
        
except Exception as e:
    print(f"❌ API connection error: {e}")
