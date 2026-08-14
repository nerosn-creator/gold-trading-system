import pandas as pd
import numpy as np
from typing import Dict, Any

def run_backtest(df: pd.DataFrame, initial_capital: float = 10000.0, position_size_oz: float = 1.0) -> Dict[str, Any]:
    """
    Simulates trades based on signal_type and calculates win rate, total return, profit factor, max drawdown.
    """
    df = df.copy()
    
    capital = initial_capital
    position = 0 # +1 for Long, -1 for Short
    entry_price = 0.0
    entry_time = None
    trades = []
    
    equity_curve = [initial_capital]

    for i in range(1, len(df)):
        curr = df.iloc[i]
        signal = curr['signal_type']
        close_price = curr['close']
        time_str = str(curr['timestamp'])

        # Check Position Exits or Reversals
        if position == 1: # Currently Long
            if signal in ["SELL", "STRONG_SELL"]: # Sell signal -> Exit Long
                profit = (close_price - entry_price) * position_size_oz
                capital += profit
                trades.append({
                    "type": "LONG",
                    "entry_time": entry_time,
                    "entry_price": float(entry_price),
                    "exit_time": time_str,
                    "exit_price": float(close_price),
                    "profit": float(round(profit, 2)),
                    "return_pct": float(round((close_price - entry_price) / entry_price * 100, 2)),
                    "win": bool(profit > 0)
                })
                position = 0

        elif position == -1: # Currently Short
            if signal in ["BUY", "STRONG_BUY"]: # Buy signal -> Exit Short
                profit = (entry_price - close_price) * position_size_oz
                capital += profit
                trades.append({
                    "type": "SHORT",
                    "entry_time": entry_time,
                    "entry_price": float(entry_price),
                    "exit_time": time_str,
                    "exit_price": float(close_price),
                    "profit": float(round(profit, 2)),
                    "return_pct": float(round((entry_price - close_price) / entry_price * 100, 2)),
                    "win": bool(profit > 0)
                })
                position = 0


        # Check Position Entries
        if position == 0:
            if signal == "STRONG_BUY" or signal == "BUY":
                position = 1
                entry_price = close_price
                entry_time = time_str
            elif signal == "STRONG_SELL" or signal == "SELL":
                position = -1
                entry_price = close_price
                entry_time = time_str

        # Track unrealized + realized equity
        unrealized = 0
        if position == 1:
            unrealized = (close_price - entry_price) * position_size_oz
        elif position == -1:
            unrealized = (entry_price - close_price) * position_size_oz
            
        equity_curve.append(capital + unrealized)

    # Convert equity curve to numpy array for drawdown calculation
    eq_arr = np.array(equity_curve)
    peak = np.maximum.accumulate(eq_arr)
    drawdown = (peak - eq_arr) / peak
    max_drawdown_pct = round(float(np.max(drawdown)) * 100, 2) if len(drawdown) > 0 else 0.0

    # Calculate metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t['win']]
    losing_trades = [t for t in trades if not t['win']]

    win_rate = round((len(winning_trades) / total_trades) * 100, 2) if total_trades > 0 else 0.0
    
    total_profit = sum(t['profit'] for t in winning_trades)
    total_loss = abs(sum(t['profit'] for t in losing_trades))
    profit_factor = round(total_profit / total_loss, 2) if total_loss > 0 else (round(total_profit, 2) if total_profit > 0 else 1.0)
    
    net_profit = round(capital - initial_capital, 2)
    total_return_pct = round((net_profit / initial_capital) * 100, 2)

    return {
        "initial_capital": float(initial_capital),
        "final_capital": float(round(capital, 2)),
        "net_profit": float(net_profit),
        "total_return_pct": float(total_return_pct),
        "total_trades": int(total_trades),
        "win_count": int(len(winning_trades)),
        "loss_count": int(len(losing_trades)),
        "win_rate_pct": float(win_rate),
        "profit_factor": float(profit_factor),
        "max_drawdown_pct": float(max_drawdown_pct),
        "recent_trades": trades[-10:] if len(trades) > 10 else trades
    }


if __name__ == "__main__":
    from data_fetcher import get_gold_candles
    from indicator_engine import calculate_indicators
    from signal_generator import generate_signals

    df = get_gold_candles("XAUUSD", "1h")
    df = calculate_indicators(df)
    df = generate_signals(df)
    res = run_backtest(df)
    print(res)
