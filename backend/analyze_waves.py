import yfinance as yf
import pandas as pd
import numpy as np

def zigzag(df, threshold=0.08):
    """
    Identifies swing highs and lows using a percentage threshold.
    threshold=0.08 means a change of at least 8% defines a new trend.
    """
    prices = df['Close'].values
    dates = df.index.values
    highs = df['High'].values
    lows = df['Low'].values
    
    swings = [] # List of tuples: (date, type, price, idx)
    
    # Initialize
    trend = 0 # 1: up, -1: down
    last_high_idx = 0
    last_low_idx = 0
    
    for i in range(1, len(df)):
        if trend == 0:
            if highs[i] >= lows[last_low_idx] * (1 + threshold):
                trend = 1
                swings.append((dates[last_low_idx], 'LOW', lows[last_low_idx], last_low_idx))
                last_high_idx = i
            elif lows[i] <= highs[last_high_idx] * (1 - threshold):
                trend = -1
                swings.append((dates[last_high_idx], 'HIGH', highs[last_high_idx], last_high_idx))
                last_low_idx = i
            else:
                if highs[i] > highs[last_high_idx]: last_high_idx = i
                if lows[i] < lows[last_low_idx]: last_low_idx = i
        elif trend == 1:
            if highs[i] > highs[last_high_idx]:
                last_high_idx = i
            elif lows[i] <= highs[last_high_idx] * (1 - threshold):
                swings.append((dates[last_high_idx], 'HIGH', highs[last_high_idx], last_high_idx))
                trend = -1
                last_low_idx = i
        elif trend == -1:
            if lows[i] < lows[last_low_idx]:
                last_low_idx = i
            elif highs[i] >= lows[last_low_idx] * (1 + threshold):
                swings.append((dates[last_low_idx], 'LOW', lows[last_low_idx], last_low_idx))
                trend = 1
                last_high_idx = i
                
    if trend == 1:
        swings.append((dates[last_high_idx], 'HIGH', highs[last_high_idx], last_high_idx))
    elif trend == -1:
        swings.append((dates[last_low_idx], 'LOW', lows[last_low_idx], last_low_idx))
        
    return swings

def analyze():
    print("Fetching GC=F daily data (2020 - 2026)...")
    df = yf.download('GC=F', start='2020-01-01', progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=['Close'])

    for thresh in [0.06, 0.08, 0.10]:
        print(f"\n=======================================================")
        print(f"       波段判定門檻 (ZigZag Threshold): {thresh*100:.0f}%")
        print(f"=======================================================")
        swings = zigzag(df, threshold=thresh)
        
        up_waves = []
        down_waves = []
        
        for i in range(len(swings) - 1):
            t1, type1, p1, idx1 = swings[i]
            t2, type2, p2, idx2 = swings[i+1]
            
            days = (pd.to_datetime(t2) - pd.to_datetime(t1)).days
            
            if type1 == 'LOW' and type2 == 'HIGH':
                # Bull wave
                gain_pct = (p2 - p1) / p1 * 100
                up_waves.append({
                    'start_date': str(pd.to_datetime(t1).date()),
                    'end_date': str(pd.to_datetime(t2).date()),
                    'start_p': p1,
                    'end_p': p2,
                    'pct': gain_pct,
                    'days': days
                })
            elif type1 == 'HIGH' and type2 == 'LOW':
                # Correction wave
                drop_pct = (p2 - p1) / p1 * 100
                # Retracement ratio of previous up wave if exists
                retrace = None
                if up_waves:
                    prev_gain = up_waves[-1]['end_p'] - up_waves[-1]['start_p']
                    if prev_gain > 0:
                        retrace = (p1 - p2) / prev_gain * 100
                        
                down_waves.append({
                    'start_date': str(pd.to_datetime(t1).date()),
                    'end_date': str(pd.to_datetime(t2).date()),
                    'start_p': p1,
                    'end_p': p2,
                    'pct': drop_pct,
                    'days': days,
                    'retrace_pct': retrace
                })
                
        df_up = pd.DataFrame(up_waves)
        df_down = pd.DataFrame(down_waves)
        
        print(f"\n【波段上漲統計 (Bull Waves)】 共 {len(df_up)} 次")
        print(f"  平均上漲幅度: {df_up['pct'].mean():.2f}%")
        print(f"  中位數漲幅:   {df_up['pct'].median():.2f}%")
        print(f"  最小 ~ 最大:  {df_up['pct'].min():.2f}% ~ {df_up['pct'].max():.2f}%")
        print(f"  平均持續天數: {df_up['days'].mean():.1f} 天 (約 {df_up['days'].mean()/30:.1f} 個月)")
        print(f"  漲幅區間分布:")
        print(f"    6% ~ 12%:   {len(df_up[(df_up['pct']>=6) & (df_up['pct']<12)])} 次 ({len(df_up[(df_up['pct']>=6) & (df_up['pct']<12)])/len(df_up)*100:.1f}%)")
        print(f"    12% ~ 18%:  {len(df_up[(df_up['pct']>=12) & (df_up['pct']<18)])} 次 ({len(df_up[(df_up['pct']>=12) & (df_up['pct']<18)])/len(df_up)*100:.1f}%)")
        print(f"    18% ~ 25%:  {len(df_up[(df_up['pct']>=18) & (df_up['pct']<25)])} 次 ({len(df_up[(df_up['pct']>=18) & (df_up['pct']<25)])/len(df_up)*100:.1f}%)")
        print(f"    > 25% (大主升浪): {len(df_up[df_up['pct']>=25])} 次 ({len(df_up[df_up['pct']>=25])/len(df_up)*100:.1f}%)")
        
        print(f"\n【波段回檔統計 (Correction Waves)】 共 {len(df_down)} 次")
        print(f"  平均回檔幅度: {df_down['pct'].mean():.2f}%")
        print(f"  中位數跌幅:   {df_down['pct'].median():.2f}%")
        print(f"  最小 ~ 最大:  {df_down['pct'].max():.2f}% ~ {df_down['pct'].min():.2f}%")
        print(f"  平均持續天數: {df_down['days'].mean():.1f} 天 (約 {df_down['days'].mean()/30:.1f} 個月)")
        if 'retrace_pct' in df_down.columns and df_down['retrace_pct'].dropna().any():
            print(f"  平均斐波那契回撤率 (前一波漲幅的%): {df_down['retrace_pct'].mean():.1f}% (中位數: {df_down['retrace_pct'].median():.1f}%)")
        print(f"  跌幅區間分布:")
        print(f"    -6% ~ -10%:  {len(df_down[(df_down['pct']<=-6) & (df_down['pct']>-10)])} 次 ({len(df_down[(df_down['pct']<=-6) & (df_down['pct']>-10)])/len(df_down)*100:.1f}%)")
        print(f"    -10% ~ -15%: {len(df_down[(df_down['pct']<=-10) & (df_down['pct']>-15)])} 次 ({len(df_down[(df_down['pct']<=-10) & (df_down['pct']>-15)])/len(df_down)*100:.1f}%)")
        print(f"    -15% ~ -20%: {len(df_down[(df_down['pct']<=-15) & (df_down['pct']>-20)])} 次 ({len(df_down[(df_down['pct']<=-15) & (df_down['pct']>-20)])/len(df_down)*100:.1f}%)")
        print(f"    > -20% (深幅修正): {len(df_down[df_down['pct']<=-20])} 次 ({len(df_down[df_down['pct']<=-20])/len(df_down)*100:.1f}%)")

        if thresh == 0.08:
            print("\n【門檻 8% 近年所有波段明細 (2020~2026)】:")
            for j in range(min(len(df_up), len(df_down))):
                u = df_up.iloc[j]
                d = df_down.iloc[j]
                print(f"  波段 #{j+1:02d} 上漲: {u['start_date']} ({u['start_p']:.1f}) -> {u['end_date']} ({u['end_p']:.1f}) | 漲幅: {u['pct']:+6.2f}% | 歷時: {u['days']:3d}天")
                print(f"          回檔: {d['start_date']} ({d['start_p']:.1f}) -> {d['end_date']} ({d['end_p']:.1f}) | 跌幅: {d['pct']:+6.2f}% | 歷時: {d['days']:3d}天 | 回撤前波: {d['retrace_pct']:.1f}%")

if __name__ == '__main__':
    analyze()
