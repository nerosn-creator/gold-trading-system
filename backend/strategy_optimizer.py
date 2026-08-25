import os
import json
import numpy as np
import pandas as pd
from backtester import run_backtest
from indicator_engine import calculate_indicators

import tempfile

WEIGHTS_FILE = os.path.join(os.path.dirname(__file__), "evolved_weights.json")
TMP_WEIGHTS_FILE = os.path.join(tempfile.gettempdir(), "evolved_weights.json")

DEFAULT_WEIGHTS = {
    "ema_weight": 30,
    "macd_weight": 25,
    "rsi_weight": 20,
    "bb_weight": 15,
    "stoch_weight": 10,
    "adx_threshold": 20,
    "generation": 1,
    "win_rate_pct": 54.17,
    "total_return_pct": 23.42,
    "last_updated": "2026-08-12"
}

def load_evolved_weights():
    for target in [TMP_WEIGHTS_FILE, WEIGHTS_FILE]:
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return DEFAULT_WEIGHTS.copy()

def save_evolved_weights(weights):
    saved = False
    try:
        with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
            json.dump(weights, f, ensure_ascii=False, indent=2)
        saved = True
    except Exception:
        pass
    if not saved:
        try:
            with open(TMP_WEIGHTS_FILE, "w", encoding="utf-8") as f:
                json.dump(weights, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def run_parameter_simulation(df, weights):
    """
    Simulates signals using specific indicator weights and calculates backtest win rate.
    """
    df_sim = df.copy()
    ema_w = weights["ema_weight"]
    macd_w = weights["macd_weight"]
    rsi_w = weights["rsi_weight"]
    bb_w = weights["bb_weight"]
    stoch_w = weights["stoch_weight"]
    adx_thresh = weights.get("adx_threshold", 20)

    scores = []
    reasons_list = []

    for i in range(len(df_sim)):
        row = df_sim.iloc[i]
        score = 0
        reasons = []

        # 1. EMA Crossover
        if not pd.isna(row['ema_9']) and not pd.isna(row['ema_21']):
            if row['ema_9'] > row['ema_21']:
                score += ema_w
                reasons.append("EMA 金叉")
            else:
                score -= ema_w
                reasons.append("EMA 死叉")

        # 2. MACD Histogram
        if not pd.isna(row['macd_hist']):
            if row['macd_hist'] > 0:
                score += macd_w
                reasons.append("MACD 多頭")
            else:
                score -= macd_w
                reasons.append("MACD 空頭")

        # 3. RSI Overbought/Oversold
        if not pd.isna(row['rsi_14']):
            if row['rsi_14'] < 35:
                score += rsi_w
                reasons.append("RSI 超賣")
            elif row['rsi_14'] > 65:
                score -= rsi_w
                reasons.append("RSI 超買")

        # 4. Bollinger Bands
        if not pd.isna(row['bb_lower']) and not pd.isna(row['bb_upper']):
            if row['close'] <= row['bb_lower']:
                score += bb_w
                reasons.append("觸及布林下軌")
            elif row['close'] >= row['bb_upper']:
                score -= bb_w
                reasons.append("觸及布林上軌")

        # 5. Stochastic KD
        if not pd.isna(row['stoch_k']) and not pd.isna(row['stoch_d']):
            if row['stoch_k'] > row['stoch_d'] and row['stoch_k'] < 40:
                score += stoch_w
                reasons.append("KD 金叉")
            elif row['stoch_k'] < row['stoch_d'] and row['stoch_k'] > 60:
                score -= stoch_w
                reasons.append("KD 死叉")

        # 6. ADX Filter
        if not pd.isna(row['adx_14']) and row['adx_14'] < adx_thresh:
            score = int(score * 0.5)

        scores.append(score)
        reasons_list.append(reasons)

    df_sim['signal_score'] = scores
    df_sim['signal_reasons'] = reasons_list

    # Determine Signal Type
    def classify_signal(score):
        if score >= 55:
            return "STRONG_BUY"
        elif score >= 25:
            return "BUY"
        elif score <= -55:
            return "STRONG_SELL"
        elif score <= -25:
            return "SELL"
        return "NEUTRAL"

    df_sim['signal_type'] = df_sim['signal_score'].apply(classify_signal)
    df_sim['take_profit'] = df_sim['close'] * 1.015
    df_sim['stop_loss'] = df_sim['close'] * 0.988

    res = run_backtest(df_sim)
    return res["win_rate_pct"], res["total_return_pct"], res["profit_factor"]

def auto_optimize_strategy(df):
    """
    Grid-search optimizer to auto-tune indicator weights and maximize win rate.
    """
    if df.empty or len(df) < 50:
        return load_evolved_weights()

    curr_weights = load_evolved_weights()
    best_weights = curr_weights.copy()
    best_win_rate = curr_weights.get("win_rate_pct", 50.0)
    best_return = curr_weights.get("total_return_pct", 0.0)

    # Candidate weight distributions
    candidate_configs = [
        {"ema_weight": 35, "macd_weight": 25, "rsi_weight": 20, "bb_weight": 10, "stoch_weight": 10, "adx_threshold": 22},
        {"ema_weight": 40, "macd_weight": 20, "rsi_weight": 20, "bb_weight": 10, "stoch_weight": 10, "adx_threshold": 25},
        {"ema_weight": 25, "macd_weight": 35, "rsi_weight": 20, "bb_weight": 10, "stoch_weight": 10, "adx_threshold": 20},
        {"ema_weight": 30, "macd_weight": 30, "rsi_weight": 25, "bb_weight": 10, "stoch_weight": 5, "adx_threshold": 20},
        {"ema_weight": 25, "macd_weight": 25, "rsi_weight": 25, "bb_weight": 15, "stoch_weight": 10, "adx_threshold": 18},
        {"ema_weight": 45, "macd_weight": 20, "rsi_weight": 15, "bb_weight": 10, "stoch_weight": 10, "adx_threshold": 22},
    ]

    for config in candidate_configs:
        win_rate, total_ret, pf = run_parameter_simulation(df, config)
        if win_rate > best_win_rate or (win_rate == best_win_rate and total_ret > best_return):
            best_win_rate = win_rate
            best_return = total_ret
            best_weights = config.copy()
            best_weights["win_rate_pct"] = win_rate
            best_weights["total_return_pct"] = total_ret

    # Increment generation
    best_weights["generation"] = curr_weights.get("generation", 1) + 1
    from datetime import datetime
    best_weights["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_evolved_weights(best_weights)
    return best_weights
