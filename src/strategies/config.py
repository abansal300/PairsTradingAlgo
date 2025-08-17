from dataclasses import dataclass

@dataclass
class PairsConfig:
    # Stock pairs
    stock1: str = "AAPL"
    stock2: str = "MSFT"
    
    # Strategy parameters
    lookback_days: int = 30
    entry_threshold: float = 2.0
    exit_threshold: float = 0.5
    
    # Risk management
    max_position_size: float = 0.05
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    
    # Execution
    check_interval: int = 300  # 5 minutes
    paper_trading: bool = True 