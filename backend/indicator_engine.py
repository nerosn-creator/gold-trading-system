import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates technical indicators for Gold market data:
    - Moving Averages (EMA 9, 21, 50; SMA 20, 50, 200)
    - MACD (12, 26, 9)
    - RSI (14)
    - Bollinger Bands (20, 2)
    - ATR (14)
    - Stochastic Oscillator KD (14, 3, 3)
    - SuperTrend (10, 3)
    """
    df = df.copy()

    # 1. Moving Averages
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()

    # 2. MACD (12, 26, 9)
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd_line'] = ema_12 - ema_26
    df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd_line'] - df['macd_signal']

    # 3. RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss.replace(0, np.nan))
    df['rsi_14'] = 100 - (100 / (1 + rs))
    df['rsi_14'] = df['rsi_14'].fillna(50)

    # 4. Bollinger Bands (20, 2)
    bb_std = df['close'].rolling(window=20).std()
    df['bb_middle'] = df['sma_20']
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']).replace(0, np.nan)

    # 5. ATR (14) - Average True Range
    high_low = df['high'] - df['low']
    high_prev_close = (df['high'] - df['close'].shift(1)).abs()
    low_prev_close = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(window=14).mean().bfill()


    # 6. Stochastic Oscillator KD (14, 3, 3)
    low_14 = df['low'].rolling(window=14).min()
    high_14 = df['high'].rolling(window=14).max()
    k_fast = 100 * ((df['close'] - low_14) / (high_14 - low_14).replace(0, np.nan))
    df['stoch_k'] = k_fast.rolling(window=3).mean().fillna(50)
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean().fillna(50)

    # 7. ADX (14) - Average Directional Index (Trend Strength)
    up_move = df['high'] - df['high'].shift(1)
    down_move = df['low'].shift(1) - df['low']
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr_smooth = df['atr_14']
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / tr_smooth.replace(0, np.nan))
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / tr_smooth.replace(0, np.nan))
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan))
    df['adx_14'] = dx.rolling(14).mean().bfill().fillna(20)

    # 8. Trend Direction & Signal Score Helper Indicators
    df['trend_bullish'] = (df['close'] > df['ema_50']) & (df['ema_9'] > df['ema_21'])
    df['trend_bearish'] = (df['close'] < df['ema_50']) & (df['ema_9'] < df['ema_21'])


    return df

if __name__ == "__main__":
    from data_fetcher import get_gold_candles
    df = get_gold_candles("XAUUSD", "1h")
    df_ind = calculate_indicators(df)
    print(df_ind[['timestamp', 'close', 'macd_hist', 'rsi_14', 'bb_pct', 'atr_14']].tail())
