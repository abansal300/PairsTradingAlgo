# Automated Pairs Trading Algorithm

A sophisticated algorithmic trading system that implements pairs trading strategies using the Alpaca API.

## 🚀 Features

- **Automated Signal Detection**: Uses statistical analysis to identify trading opportunities
- **Risk Management**: Built-in position sizing and stop-loss mechanisms
- **Real-time Monitoring**: Continuously monitors market conditions
- **Paper Trading**: Safe testing environment with simulated money
- **Multiple Stock Pairs**: Easily configurable for different stock combinations

## ��️ Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/trading-algorithm.git
   cd trading-algorithm
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys**
   ```bash
   cp .env.example .env
   # Edit .env with your Alpaca API keys
   ```

## 📊 Usage

### **Run the Strategy**
```bash
python run_pairs.py
```

### **Check Account Status**
```bash
python main.py account
```

### **View Positions**
```bash
python main.py positions
```

### **Backtest Strategy**
```bash
python backtest_strategy.py
```

## 🎯 Strategy Logic

The algorithm implements a mean-reversion pairs trading strategy:

1. **Signal Detection**: Monitors price ratios between correlated stocks
2. **Entry Criteria**: Enters when Z-score exceeds threshold
3. **Position Management**: Automatically sizes positions based on account value
4. **Exit Strategy**: Exits when spread normalizes

- [Alpaca Trading API](https://alpaca.markets/)
- [Pairs Trading Strategy](https://en.wikipedia.org/wiki/Pairs_trade)