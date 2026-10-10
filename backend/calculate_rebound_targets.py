import yfinance as yf
import pandas as pd
import numpy as np

def calculate():
    # Download 1y GC=F
    df = yf.download('GC=F', period='1y', interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA100'] = df['Close'].rolling(100).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()

    # Peak in recent months (July - Sept 2026)
    recent_window = df[df.index >= '2026-06-01']
    max_idx = recent_window['High'].idxmax()
    peak_high = float(recent_window.loc[max_idx, 'High'])
    peak_close = float(recent_window.loc[max_idx, 'Close'])

    # Wave trough prior to peak
    trough_window = df[(df.index >= '2026-05-01') & (df.index <= max_idx)]
    min_idx = trough_window['Low'].idxmin()
    wave_low = float(trough_window.loc[min_idx, 'Low'])

    latest_date = df.index[-1]
    curr_price = float(df.loc[latest_date, 'Close'])

    # Pullback low so far
    pb_window = df[df.index >= max_idx]
    pb_low_idx = pb_window['Low'].idxmin()
    pb_low = float(pb_window.loc[pb_low_idx, 'Low'])

    wave_gain = peak_high - wave_low
    wave_gain_pct = (peak_high - wave_low) / wave_low * 100

    curr_dd = (curr_price - peak_high) / peak_high * 100
    max_dd_so_far = (pb_low - peak_high) / peak_high * 100

    print("================== 當前波段結構與位置 ================")
    print(f"前波起漲低點 (Wave Low): {wave_low:.1f} ({min_idx.date()})")
    print(f"波段歷史高點 (Wave Peak): {peak_high:.1f} (收盤 {peak_close:.1f}, {max_idx.date()})")
    print(f"本波上漲累計幅度: +{wave_gain_pct:.2f}% (+{wave_gain:.1f} 美元)")
    print(f"目前最新價格: {curr_price:.1f} 美元")
    print(f"本波回檔最低點: {pb_low:.1f} 美元 ({pb_low_idx.date()})")
    print(f"目前距高點回檔幅度: {curr_dd:.2f}%")
    print(f"至今最大回檔幅度: {max_dd_so_far:.2f}%")

    print("\n================== 均線支撐 (Moving Averages) ================")
    sma20 = float(df.loc[latest_date, 'SMA20'])
    sma50 = float(df.loc[latest_date, 'SMA50'])
    sma100 = float(df.loc[latest_date, 'SMA100'])
    sma200 = float(df.loc[latest_date, 'SMA200']) if not pd.isna(df.loc[latest_date, 'SMA200']) else np.nan

    print(f"20 日月線 (SMA20):   {sma20:.1f} 美元")
    print(f"50 日季線 (SMA50):   {sma50:.1f} 美元")
    print(f"100 日半年線 (SMA100): {sma100:.1f} 美元")
    print(f"200 日年線 (SMA200):  {sma200:.1f} 美元")

    print("\n================== 歷史統計回檔梯度與回補目標點 ================")
    # Drawdown tiers from peak
    dd_8 = peak_high * (1 - 0.08)
    dd_10 = peak_high * (1 - 0.10)
    dd_12_5 = peak_high * (1 - 0.1257) # median pullback from backtest
    dd_13_6 = peak_high * (1 - 0.1357) # mean pullback
    dd_15 = peak_high * (1 - 0.15)
    dd_18 = peak_high * (1 - 0.18)

    print(f"【第一回補區｜短線強勢回檔 (-8% ~ -10%)】:  {dd_8:.1f} ~ {dd_10:.1f} 美元")
    print(f"【第二回補區｜常態波段中位數 (-12.6% ~ -13.6%)】: {dd_12_5:.1f} ~ {dd_13_6:.1f} 美元")
    print(f"【第三回補區｜深度洗盤極限 (-15% ~ -18%)】: {dd_15:.1f} ~ {dd_18:.1f} 美元")

    print("\n================== 斐波那契回撤支撐 (Fibonacci Retracement) ================")
    fib_236 = peak_high - wave_gain * 0.236
    fib_382 = peak_high - wave_gain * 0.382
    fib_500 = peak_high - wave_gain * 0.500
    fib_618 = peak_high - wave_gain * 0.618

    print(f"Fibonacci 0.236: {fib_236:.1f} 美元 (回跌 {(fib_236-peak_high)/peak_high*100:.2f}%)")
    print(f"Fibonacci 0.382: {fib_382:.1f} 美元 (回跌 {(fib_382-peak_high)/peak_high*100:.2f}%)")
    print(f"Fibonacci 0.500: {fib_500:.1f} 美元 (回跌 {(fib_500-peak_high)/peak_high*100:.2f}%)")
    print(f"Fibonacci 0.618: {fib_618:.1f} 美元 (回跌 {(fib_618-peak_high)/peak_high*100:.2f}%)")

    # Fetch USD/TWD for Taiwan gold conversion
    fx = yf.Ticker('USDTWD=X').history(period='5d')
    fx_rate = float(fx['Close'].iloc[-1]) if not fx.empty else 32.0
    print(f"\n目前參考匯率 (USD/TWD): {fx_rate:.2f}")

    print("\n換算台灣銀樓牌價（約每台錢，係數 8.294 + 銀樓工本溢價約 8%）:")
    def to_twd_chien(usd):
        # 1 oz = 8.29426 台錢. Silver shop sell price ~ (usd * fx / 8.294) * 1.08
        return (usd * fx_rate / 8.29426) * 1.06

    print(f"目前價位 ({curr_price:.0f}): 約 {to_twd_chien(curr_price):,.0f} 元/錢")
    print(f"常態回補中位 ({dd_12_5:.0f}): 約 {to_twd_chien(dd_12_5):,.0f} 元/錢")
    print(f"深洗回補低點 ({dd_15:.0f}): 約 {to_twd_chien(dd_15):,.0f} 元/錢")

if __name__ == '__main__':
    calculate()
