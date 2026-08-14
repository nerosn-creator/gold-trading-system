import pandas as pd
import numpy as np
from typing import Dict, List, Any

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluates multi-indicator rules and generates dynamic buy/sell scores & signals for Gold.
    """
    df = df.copy()
    
    signal_scores = []
    signal_types = []
    tp_prices = []
    sl_prices = []
    reasons = []

    for i in range(len(df)):
        if i < 20: # Not enough data for stable indicator calculation
            signal_scores.append(0)
            signal_types.append("NEUTRAL")
            tp_prices.append(0.0)
            sl_prices.append(0.0)
            reasons.append(["等待技術指標計算"])
            continue

        curr = df.iloc[i]
        prev = df.iloc[i-1]

        score = 0
        rule_hits = []

        # 1. EMA Trend & Golden/Death Cross
        ema9_curr, ema9_prev = curr['ema_9'], prev['ema_9']
        ema21_curr, ema21_prev = curr['ema_21'], prev['ema_21']
        close_curr = curr['close']

        if ema9_prev <= ema21_prev and ema9_curr > ema21_curr:
            score += 30
            rule_hits.append("EMA 9/21 黃金交叉 (Bullish Cross)")
        elif ema9_prev >= ema21_prev and ema9_curr < ema21_curr:
            score -= 30
            rule_hits.append("EMA 9/21 死亡交叉 (Bearish Cross)")

        if close_curr > curr['ema_50']:
            score += 10
            rule_hits.append("金價位於 50 EMA 上方 (多頭趨勢)")
        else:
            score -= 10
            rule_hits.append("金價位於 50 EMA 下方 (空頭趨勢)")

        # 2. MACD Histogram & Crossover
        macd_curr, macd_prev = curr['macd_line'], prev['macd_line']
        sig_curr, sig_prev = curr['macd_signal'], prev['macd_signal']

        if macd_prev <= sig_prev and macd_curr > sig_curr:
            score += 25
            rule_hits.append("MACD 線向上金叉訊號線")
        elif macd_prev >= sig_prev and macd_curr < sig_curr:
            score -= 25
            rule_hits.append("MACD 線向下死叉訊號線")

        if curr['macd_hist'] > 0 and curr['macd_hist'] > prev['macd_hist']:
            score += 10
            rule_hits.append("MACD 柱狀體擴張 (多頭動能加強)")
        elif curr['macd_hist'] < 0 and curr['macd_hist'] < prev['macd_hist']:
            score -= 10
            rule_hits.append("MACD 柱狀體收縮 (空頭動能加強)")

        # 3. RSI Overbought / Oversold
        rsi = curr['rsi_14']
        if rsi < 30:
            score += 25
            rule_hits.append(f"RSI 超賣區域 ({rsi:.1f} < 30) - 潛在反彈")
        elif rsi > 70:
            score -= 25
            rule_hits.append(f"RSI 超買區域 ({rsi:.1f} > 70) - 潛在回檔")
        elif 50 <= rsi <= 65:
            score += 10
        elif 35 <= rsi < 50:
            score -= 10

        # 4. Bollinger Bands Reversion / Breakout
        if close_curr <= curr['bb_lower']:
            score += 20
            rule_hits.append("金價觸及布林通道下軌 (超賣反彈機會)")
        elif close_curr >= curr['bb_upper']:
            score -= 20
            rule_hits.append("金價觸及布林通道上軌 (超買回調風險)")

        # 5. Stochastic KD
        stoch_k, stoch_d = curr['stoch_k'], curr['stoch_d']
        stoch_k_prev, stoch_d_prev = prev['stoch_k'], prev['stoch_d']

        if stoch_k_prev <= stoch_d_prev and stoch_k > stoch_d and stoch_k < 30:
            score += 15
            rule_hits.append("KD 低檔金叉 (強烈買進訊號)")
        elif stoch_k_prev >= stoch_d_prev and stoch_k < stoch_d and stoch_k > 70:
            score -= 15
            rule_hits.append("KD 高檔死叉 (強烈賣出訊號)")

        # 6. ADX Trend Strength Filter (防震盪巴刷)
        adx = curr.get('adx_14', 20)
        if adx >= 25:
            if score > 0: score += 15
            elif score < 0: score -= 15
            rule_hits.append(f"ADX 趨勢強度顯著 ({adx:.1f} >= 25)")
        elif adx < 18:
            score = int(score * 0.5) # Scale down score in weak trend consolidation
            rule_hits.append(f"ADX 處於無趨勢盤整區 ({adx:.1f} < 18) - 觀望防刷")

        # Normalize Signal Category (Stricter Thresholds for Higher Precision)
        if score >= 50:
            sig_type = "STRONG_BUY"
        elif score >= 35:
            sig_type = "BUY"
        elif score <= -50:
            sig_type = "STRONG_SELL"
        elif score <= -35:
            sig_type = "SELL"
        else:
            sig_type = "NEUTRAL"

        # Calculate Stop Loss (SL) & Take Profit (TP) with 2:1+ Risk-Reward Ratio
        atr = curr['atr_14'] if not np.isnan(curr['atr_14']) else 5.0
        
        if "BUY" in sig_type:
            sl = round(close_curr - (1.4 * atr), 2)
            tp = round(close_curr + (3.0 * atr), 2)
        elif "SELL" in sig_type:
            sl = round(close_curr + (1.4 * atr), 2)
            tp = round(close_curr - (3.0 * atr), 2)
        else:
            sl = round(close_curr - (1.0 * atr), 2)
            tp = round(close_curr + (1.0 * atr), 2)


        signal_scores.append(score)
        signal_types.append(sig_type)
        sl_prices.append(sl)
        tp_prices.append(tp)
        reasons.append(rule_hits)

    df['signal_score'] = signal_scores
    df['signal_type'] = signal_types
    df['stop_loss'] = sl_prices
    df['take_profit'] = tp_prices
    df['signal_reasons'] = reasons

    return df

def get_latest_signal_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Extract latest signal metrics for API dashboard response."""
    if df is None or df.empty:
        return {}

    latest = df.iloc[-1]

    # Calculate True Today's (Daily Trading Session) Open, High, Low, Range & Change
    latest_dt = pd.to_datetime(latest['timestamp'])
    today_date = latest_dt.date()
    today_df = df[df['timestamp'].dt.date == today_date]
    if today_df.empty:
        today_df = df.tail(24)

    day_open = float(today_df.iloc[0]['open'])
    day_high = float(today_df['high'].max())
    day_low = float(today_df['low'].min())

    prev_days_df = df[df['timestamp'].dt.date < today_date]
    if not prev_days_df.empty:
        prev_close = float(prev_days_df.iloc[-1]['close'])
    else:
        prev_close = day_open

    price_change = round(float(latest['close']) - prev_close, 2)
    price_change_pct = round((price_change / prev_close) * 100, 2) if prev_close > 0 else 0.0

    return {
        "timestamp": str(latest['timestamp']),
        "symbol": "XAU/USD (Gold)",
        "current_price": float(latest['close']),
        "open": round(day_open, 2),
        "high": round(day_high, 2),
        "low": round(day_low, 2),
        "price_change": price_change,
        "price_change_pct": price_change_pct,
        "signal_type": str(latest['signal_type']),
        "signal_score": int(latest['signal_score']),
        "take_profit": float(latest['take_profit']),
        "stop_loss": float(latest['stop_loss']),
        "rsi_14": round(float(latest['rsi_14']), 2),
        "macd_hist": round(float(latest['macd_hist']), 2),
        "atr_14": round(float(latest['atr_14']), 2),
        "ema_9": round(float(latest['ema_9']), 2),
        "ema_21": round(float(latest['ema_21']), 2),
        "ema_50": round(float(latest['ema_50']), 2),
        "reasons": latest['signal_reasons']
    }

if __name__ == "__main__":
    from data_fetcher import get_gold_candles
    from indicator_engine import calculate_indicators
    
    df = get_gold_candles("XAUUSD", "1h")
    df = calculate_indicators(df)
    df = generate_signals(df)
    summary = get_latest_signal_summary(df)
    print(summary)
