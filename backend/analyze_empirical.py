import yfinance as yf
import pandas as pd
import numpy as np

def run_analysis():
    # 1. Download Gold Futures GC=F hourly data
    print("Downloading GC=F (1h)...")
    gc = yf.download('GC=F', period='1y', interval='1h', progress=False)
    if isinstance(gc.columns, pd.MultiIndex):
        gc.columns = gc.columns.get_level_values(0)
    if gc.index.tz is None:
        gc.index = gc.index.tz_localize('UTC').tz_convert('Asia/Taipei')
    else:
        gc.index = gc.index.tz_convert('Asia/Taipei')

    # 2. Download 00635U.TW daily data (Taiwan Stock Exchange Gold ETF)
    print("Downloading 00635U.TW (1d)...")
    tw = yf.download('00635U.TW', period='1y', interval='1d', progress=False)
    if isinstance(tw.columns, pd.MultiIndex):
        tw.columns = tw.columns.get_level_values(0)
    if tw.index.tz is None:
        tw.index = tw.index.tz_localize('Asia/Taipei')
    else:
        tw.index = tw.index.tz_convert('Asia/Taipei')

    # 3. Download USD/TWD exchange rate
    print("Downloading USDTWD=X (1d)...")
    fx = yf.download('USDTWD=X', period='1y', interval='1d', progress=False)
    if isinstance(fx.columns, pd.MultiIndex):
        fx.columns = fx.columns.get_level_values(0)
    if fx.index.tz is None:
        fx.index = fx.index.tz_localize('Asia/Taipei')
    else:
        fx.index = fx.index.tz_convert('Asia/Taipei')

    tw_dates = tw.index.date
    rows = []

    for i in range(len(tw)-1):
        d_curr = tw_dates[i]
        d_next = tw_dates[i+1]

        # GC price at Taiwan market close (13:30 - 15:30)
        sub_gc_curr = gc[(gc.index.date == d_curr) & (gc.index.hour >= 13) & (gc.index.hour <= 16)]
        # GC price at Taiwan market open next day (08:30 - 09:30)
        sub_gc_next = gc[(gc.index.date == d_next) & (gc.index.hour >= 8) & (gc.index.hour <= 10)]

        if sub_gc_curr.empty or sub_gc_next.empty:
            continue

        p_gc_close = float(sub_gc_curr['Close'].iloc[-1])
        p_gc_open = float(sub_gc_next['Open'].iloc[0])
        gc_overnight_ret = (p_gc_open - p_gc_close) / p_gc_close

        # Intraday GC on d_curr
        sub_gc_curr_open = gc[(gc.index.date == d_curr) & (gc.index.hour >= 8) & (gc.index.hour <= 10)]
        p_gc_curr_open = float(sub_gc_curr_open['Open'].iloc[0]) if not sub_gc_curr_open.empty else p_gc_close
        gc_daytime_ret = (p_gc_close - p_gc_curr_open) / p_gc_curr_open
        gc_24h_ret = (p_gc_open - p_gc_curr_open) / p_gc_curr_open

        # TW ETF
        p_tw_prev_close = float(tw.iloc[i]['Close'])
        p_tw_next_open = float(tw.iloc[i+1]['Open'])
        p_tw_next_close = float(tw.iloc[i+1]['Close'])

        if pd.isna(p_tw_prev_close) or pd.isna(p_tw_next_open) or p_tw_prev_close == 0:
            continue

        tw_open_ret = (p_tw_next_open - p_tw_prev_close) / p_tw_prev_close
        tw_close_ret = (p_tw_next_close - p_tw_prev_close) / p_tw_prev_close

        # FX change
        fx_sub_curr = fx[fx.index.date == d_curr]
        fx_sub_next = fx[fx.index.date == d_next]
        fx_c = float(fx_sub_curr['Close'].iloc[0]) if not fx_sub_curr.empty else np.nan
        fx_n = float(fx_sub_next['Close'].iloc[0]) if not fx_sub_next.empty else np.nan
        fx_ret = (fx_n - fx_c) / fx_c if (not pd.isna(fx_c) and not pd.isna(fx_n)) else 0.0

        # Theoretical TWD gold overnight return
        twd_gold_ret = ((p_gc_open * (fx_n if not pd.isna(fx_n) else 32.0)) / 
                        (p_gc_close * (fx_c if not pd.isna(fx_c) else 32.0))) - 1

        rows.append({
            'd_curr': d_curr,
            'd_next': d_next,
            'p_gc_close': p_gc_close,
            'p_gc_open': p_gc_open,
            'gc_daytime_ret': gc_daytime_ret,
            'gc_overnight_ret': gc_overnight_ret,
            'gc_24h_ret': gc_24h_ret,
            'fx_ret': fx_ret,
            'twd_gold_ret': twd_gold_ret,
            'tw_open_ret': tw_open_ret,
            'tw_close_ret': tw_close_ret
        })

    df = pd.DataFrame(rows)
    print("\n================== 近一年統計結果 (Quantitative Report) ==================")
    print(f"有效交易日配對總數 (Total Analyzed Trading Days): {len(df)}")

    # 1. Overall correlation
    corr_open = df['gc_overnight_ret'].corr(df['tw_open_ret'])
    corr_close = df['gc_overnight_ret'].corr(df['tw_close_ret'])
    print(f"國際金價夜盤報酬率 與 台灣市場次日開盤報酬率 相關係數: {corr_open:.4f}")
    print(f"國際金價夜盤報酬率 與 台灣市場次日收盤報酬率 相關係數: {corr_close:.4f}")

    # 2. When international gold fell overnight
    gc_down = df[df['gc_overnight_ret'] < 0]
    total_down = len(gc_down)
    tw_down = len(gc_down[gc_down['tw_open_ret'] < -0.0005])
    tw_flat = len(gc_down[abs(gc_down['tw_open_ret']) <= 0.0005])
    tw_up = len(gc_down[gc_down['tw_open_ret'] > 0.0005])

    print(f"\n【情境一：台灣收盤後，國際金價夜盤下跌 (GC Overnight < 0%)】")
    print(f"總計發生天數: {total_down} 天 (佔整體交易日約 {total_down/len(df)*100:.1f}%)")
    print(f" -> 隔日台灣市場開盤【下跌】: {tw_down} 天 ({tw_down/total_down*100:.1f}%)  <-- 正常同向聯動")
    print(f" -> 隔日台灣市場開盤【持平】: {tw_flat} 天 ({tw_flat/total_down*100:.1f}%)")
    print(f" -> 隔日台灣市場開盤【上漲】: {tw_up} 天 ({tw_up/total_down*100:.1f}%)  <-- 使用者觀察的反向情況")

    # 3. When international gold fell significantly (e.g. < -0.3%)
    gc_down_sig = df[df['gc_overnight_ret'] < -0.003]
    total_down_sig = len(gc_down_sig)
    tw_down_sig = len(gc_down_sig[gc_down_sig['tw_open_ret'] < -0.0005])
    tw_up_sig = len(gc_down_sig[gc_down_sig['tw_open_ret'] > 0.0005])

    print(f"\n【情境二：國際金價夜盤明顯下跌 (跌幅 > 0.3%)】")
    print(f"總計發生天數: {total_down_sig} 天")
    print(f" -> 隔日台灣市場開盤【下跌】: {tw_down_sig} 天 ({tw_down_sig/total_down_sig*100:.1f}%)")
    print(f" -> 隔日台灣市場開盤【上漲】: {tw_up_sig} 天 ({tw_up_sig/total_down_sig*100:.1f}%)")

    # 4. Detailed analysis of the counter-trend days (tw_up)
    counter_cases = gc_down[gc_down['tw_open_ret'] > 0.0005]
    print(f"\n【反向異常案例深度剖析 (共 {len(counter_cases)} 天)】")
    # How many of these counter cases had positive 24h return (daytime surged prior to overnight drop)?
    pos_24h = len(counter_cases[counter_cases['gc_24h_ret'] > 0])
    # How many had positive USD/TWD fx return (TWD depreciated)?
    pos_fx = len(counter_cases[counter_cases['fx_ret'] > 0.001])
    
    print(f"1. 雖然夜盤下跌，但前一天白天已大漲 (24小時累計仍上漲): {pos_24h} 天 ({pos_24h/len(counter_cases)*100:.1f}%)")
    print(f"2. 美元兌台幣升值 (台幣貶值，抵銷金價跌幅): {pos_fx} 天 ({pos_fx/len(counter_cases)*100:.1f}%)")
    
    print("\n異常案例前 10 筆詳情:")
    sample = counter_cases[['d_curr', 'd_next', 'gc_daytime_ret', 'gc_overnight_ret', 'gc_24h_ret', 'fx_ret', 'tw_open_ret']].head(10)
    for idx, r in sample.iterrows():
        print(f"日期 {r['d_curr']} -> {r['d_next']}: "
              f"前日白天國際漲跌 {r['gc_daytime_ret']*100:+.2f}%, "
              f"夜盤跌幅 {r['gc_overnight_ret']*100:+.2f}%, "
              f"24h累計 {r['gc_24h_ret']*100:+.2f}%, "
              f"匯率漲跌 {r['fx_ret']*100:+.2f}%, "
              f"台灣開盤漲跌 {r['tw_open_ret']*100:+.2f}%")

if __name__ == '__main__':
    run_analysis()
