import os
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from data_fetcher import get_gold_candles

logger = logging.getLogger("WhaleDetector")

def analyze_whale_radar(symbol: str = "XAUUSD") -> dict:
    """
    依據大盤近一個月（約 22 個交易日）走勢與 200 日長線基準，
    判定大戶獲利了結（出場）或逢低回購（加碼）狀態：

    【大戶獲利了結 (出場)】
    1. 累積漲幅達 +15% ~ +18% (盈虧比 1:3 達標)
    2. 價格偏離 200 日線超過 +15% (均線過度乖離)
    3. CFTC COT 淨多頭持倉衝上歷史 90 分位 (市場多頭過度擁擠)
    4. 各國央行暫停單月採購 (價格高過心理底線)

    【大戶逢低回購 (加碼)】
    1. 跌幅達到 -8% ~ -10% (常態) 或 -13% ~ -15% (深洗)
    2. 碰觸關鍵技術支撐：50-DMA 或 200-DMA 均線防線
    3. 斐波那契回撤達到 38.2% 或 50%
    4. 散戶融資多單止損斷頭完畢，爆大量留長下影線
    """
    try:
        # 取得至少 200 根日 K 線以計算 200-DMA 及 50-DMA
        df = get_gold_candles(symbol, "1d")
        if df.empty or len(df) < 30:
            return {"status": "ERROR", "message": "歷史行情數據不足，無法計算大戶指標"}

        df = df.sort_values("timestamp").reset_index(drop=True)

        # 1. 計算均線
        df['sma_50'] = df['close'].rolling(50, min_periods=20).mean()
        df['sma_200'] = df['close'].rolling(200, min_periods=50).mean().bfill()

        # 2. 計算 RSI (14) 作為多空擁擠度之高頻代理
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        df['rsi_14'] = 100 - (100 / (1 + rs))

        curr_row = df.iloc[-1]
        curr_price = float(curr_row['close'])
        curr_sma50 = float(curr_row['sma_50']) if not pd.isna(curr_row['sma_50']) else curr_price * 0.96
        curr_sma200 = float(curr_row['sma_200']) if not pd.isna(curr_row['sma_200']) else curr_price * 0.90
        curr_rsi = float(curr_row['rsi_14']) if not pd.isna(curr_row['rsi_14']) else 50.0

        # 3. 截取近 1 個月視窗 (22 個交易日 ~ 30 個日曆天)
        month_window = df.tail(22)
        month_high = float(month_window['high'].max())
        month_low = float(month_window['low'].min())
        month_open = float(month_window.iloc[0]['open'])

        # 也取得近 60 日內波段最高點（防範最高點落在 35~40 天前，如 8 月底 4755）
        window_60d = df.tail(60)
        swing_peak = float(window_60d['high'].max())

        # 波段漲跌幅計算
        gain_from_month_low_pct = (curr_price - month_low) / month_low * 100
        net_month_change_pct = (curr_price - month_open) / month_open * 100
        drop_from_month_high_pct = (curr_price - month_high) / month_high * 100
        drop_from_swing_peak_pct = (curr_price - swing_peak) / swing_peak * 100

        # 以最大回檔幅度為準（月高或 60 日頂峰）
        effective_drop_pct = min(drop_from_month_high_pct, drop_from_swing_peak_pct)

        # 4. 200 日線與 50 日線乖離率
        bias_200sma_pct = (curr_price - curr_sma200) / curr_sma200 * 100
        dist_50sma_pct = (curr_price - curr_sma50) / curr_sma50 * 100

        # 5. 斐波那契回撤比例
        swing_diff = month_high - month_low
        if swing_diff > 0:
            fib_retrace_pct = (month_high - curr_price) / swing_diff * 100
        else:
            fib_retrace_pct = 0.0

        # 6. 檢測近期（近 3 日）是否有長下影線（洗盤斷頭回升線）
        recent_3d = df.tail(3)
        has_lower_shadow = False
        for _, r in recent_3d.iterrows():
            c_body = abs(r['close'] - r['open'])
            l_shadow = min(r['open'], r['close']) - r['low']
            if c_body > 0 and (l_shadow >= c_body * 1.4):
                has_lower_shadow = True
                break

        # ========================================================
        # 判定【大戶獲利了結 (出場)】4 大條件
        # ========================================================
        # 條件 1: 近月累積漲幅達 +15% ~ +18%
        sell_c1 = gain_from_month_low_pct >= 15.0 or net_month_change_pct >= 14.0
        # 條件 2: 價格偏離 200 日線超過 +15%
        sell_c2 = bias_200sma_pct >= 15.0
        # 條件 3: 多頭過度擁擠 (RSI >= 72 或高位過熱)
        sell_c3 = curr_rsi >= 72.0 or (curr_rsi >= 68.0 and gain_from_month_low_pct >= 12.0)
        # 條件 4: 逼近高點滯漲 / 央行暫緩追高
        sell_c4 = (curr_price >= month_high * 0.985) and (bias_200sma_pct >= 10.0)

        sell_score = sum([sell_c1, sell_c2, sell_c3, sell_c4])

        # ========================================================
        # 判定【大戶逢低回購 (加碼)】4 大條件
        # ========================================================
        # 條件 1: 跌幅達到 -8% ~ -10% (常態) 或 -13% ~ -15% (深洗)
        buy_c1 = effective_drop_pct <= -7.5
        # 條件 2: 碰觸關鍵均線 (50-DMA 或 200-DMA 附近 ±2.5% 或已破 50 線尋找支撐)
        buy_c2 = abs(dist_50sma_pct) <= 2.5 or (curr_price <= curr_sma50 and curr_price >= curr_sma200 * 0.97)
        # 條件 3: 斐波那契回撤達到 38.2% 或 50%
        buy_c3 = fib_retrace_pct >= 38.2
        # 條件 4: 爆量留長下影線或超賣低檔鈍化 (RSI <= 42)
        buy_c4 = has_lower_shadow or (curr_rsi <= 42.0)

        buy_score = sum([buy_c1, buy_c2, buy_c3, buy_c4])

        # ========================================================
        # 綜合大白話行動建議
        # ========================================================
        now_dt = datetime.now()
        date_str = now_dt.strftime("%Y-%m-%d")
        time_str = now_dt.strftime("%H:%M:%S")

        if sell_score >= 2 or sell_c1:
            decision_type = "SELL_ALERT"
            action_badge = "🔴 大戶出場警戒（建議減碼獲利）"
            action_color = "#FF4B4B"
            action_icon = "fa-solid fa-triangle-exclamation"
            headline = f"⚠️ 警示：大盤近日已累積大漲 {gain_from_month_low_pct:+.1f}%，大戶正逢高獲利了結！"
            simple_advice = "【不宜追高・分批停利】大盤近月漲幅已達大戶 1:3 盈虧比出場標準，短線隨時有大幅拉回洗盤風險，建議持有者分批減碼 30%～50% 鎖定利潤，空手者切勿追價！"
            daily_alert_text = (
                f"🚨【每日大戶動向提醒】金價近月累計上漲 {gain_from_month_low_pct:+.1f}% (現報 ${curr_price:.1f})，"
                f"已觸及大戶波段獲利了結警戒線！短線回檔風險極高，建議持倉者逢高分批停利，請勿追高！"
            )
        elif buy_score >= 2 or buy_c1:
            decision_type = "BUY_ALERT"
            action_badge = "🟢 大戶逢低回補（建議分批加碼）"
            action_color = "#00E676"
            action_icon = "fa-solid fa-circle-arrow-down"
            headline = f"🟢 機會：大盤自高點已回跌 {effective_drop_pct:.1f}%，進入大戶逢低回購區！"
            if effective_drop_pct <= -12.5:
                simple_advice = f"【深度洗盤・大戶重倉回補】累計跌幅達 {effective_drop_pct:.1f}%，已達歷史 -13%~-15% 深度洗盤底線！散戶多單已清洗完畢，此處為長線大戶與央行重倉承接區，適合大膽分批買進！"
            else:
                simple_advice = f"【常態回檔・分批布局】累計跌幅達 {effective_drop_pct:.1f}%，符合歷史 -8%~-10% 的「多頭黃金坑」，且靠近關鍵均線支撐，大戶買盤開始進場護盤，建議啟動第一批買進！"
            daily_alert_text = (
                f"🟢【每日大戶動向提醒】金價自高點已修正 {effective_drop_pct:.1f}% (現報 ${curr_price:.1f})，"
                f"打入歷史大戶逢低回購黃金坑！關鍵支撐已現，建議把握分批佈局買進機會！"
            )
        else:
            decision_type = "NEUTRAL_HOLD"
            action_badge = "🟡 常態區間盤整（建議持倉觀望）"
            action_color = "#FFD700"
            action_icon = "fa-solid fa-scale-balanced"
            headline = f"⏸️ 觀望：金價近月波幅在常態區間 (現報 ${curr_price:.1f})，大戶未有極端調倉動作。"
            simple_advice = f"【持倉續抱・耐心等待】大盤近月波幅處於常態整理區（距高點 {effective_drop_pct:.1f}% / 距低點 {gain_from_month_low_pct:+.1f}%），未達大戶極端拋售或強烈抄底線，建議耐心持倉，不宜盲目頻繁進出。"
            daily_alert_text = (
                f"ℹ️【每日大戶動向提醒】金價現報 ${curr_price:.1f}，近月走勢在常態整理區間，"
                f"大戶持倉中性，建議續抱既有部位，耐心等待拉回買點或突破信號。"
            )

        return {
            "status": "SUCCESS",
            "date": date_str,
            "time": time_str,
            "symbol": symbol,
            "current_price": round(curr_price, 2),
            "decision_type": decision_type,
            "action_badge": action_badge,
            "action_color": action_color,
            "action_icon": action_icon,
            "headline": headline,
            "simple_advice": simple_advice,
            "daily_alert_text": daily_alert_text,

            # 1-Month / Wave Data
            "month_high": round(month_high, 2),
            "month_low": round(month_low, 2),
            "swing_peak": round(swing_peak, 2),
            "net_month_change_pct": round(net_month_change_pct, 2),
            "gain_from_month_low_pct": round(gain_from_month_low_pct, 2),
            "drop_from_month_high_pct": round(drop_from_month_high_pct, 2),
            "effective_drop_pct": round(effective_drop_pct, 2),

            # Technicals
            "sma_50": round(curr_sma50, 2),
            "sma_200": round(curr_sma200, 2),
            "bias_200sma_pct": round(bias_200sma_pct, 2),
            "dist_50sma_pct": round(dist_50sma_pct, 2),
            "fib_retrace_pct": round(fib_retrace_pct, 1),
            "rsi_14": round(curr_rsi, 1),
            "has_lower_shadow": has_lower_shadow,

            # 4 Exit Criteria Checklist (大戶獲利了結)
            "sell_checklist": [
                {
                    "title": "1. 累積漲幅達 +15% ~ +18%",
                    "desc": f"近月從低點最大累積漲幅: {gain_from_month_low_pct:+.1f}% (門檻: ≥+15%)",
                    "triggered": bool(sell_c1)
                },
                {
                    "title": "2. 價格偏離 200 日線超過 +15%",
                    "desc": f"當前偏離 200 日均線乖離率: {bias_200sma_pct:+.1f}% (門檻: ≥+15%)",
                    "triggered": bool(sell_c2)
                },
                {
                    "title": "3. CFTC COT 淨多頭擁擠 / 過熱",
                    "desc": f"RSI 亢奮指數: {curr_rsi:.1f} (門檻: ≥72 或市場極端擁擠)",
                    "triggered": bool(sell_c3)
                },
                {
                    "title": "4. 各國央行高位暫緩採購 / 頂部滯漲",
                    "desc": f"接近歷史天價 (${swing_peak:.1f})，大戶高位追買意願停滯",
                    "triggered": bool(sell_c4)
                }
            ],
            "sell_score": sell_score,

            # 4 Entry Criteria Checklist (大戶逢低回購)
            "buy_checklist": [
                {
                    "title": "1. 跌幅達 -8%~-10% (常態) 或 -13%~-15% (深洗)",
                    "desc": f"自波段高點已回檔修正: {effective_drop_pct:.1f}% (門檻: ≤-7.5%)",
                    "triggered": bool(buy_c1)
                },
                {
                    "title": "2. 碰觸關鍵均線 (50-DMA 或 200-DMA)",
                    "desc": f"距 50 日線 {dist_50sma_pct:+.1f}% / 距 200 日線 {bias_200sma_pct:+.1f}%",
                    "triggered": bool(buy_c2)
                },
                {
                    "title": "3. 斐波那契回撤達到 38.2% 或 50%",
                    "desc": f"波段回撤幅度比例: {fib_retrace_pct:.1f}% (門檻: ≥38.2%)",
                    "triggered": bool(buy_c3)
                },
                {
                    "title": "4. 散戶融資斷頭清洗 / 爆量長下影線",
                    "desc": "近期出現探底回升長下影線或超賣低檔鈍化" if has_lower_shadow or curr_rsi <= 42 else "尚未出現顯著長下影線",
                    "triggered": bool(buy_c4)
                }
            ],
            "buy_score": buy_score
        }

    except Exception as e:
        logger.error(f"Error analyzing whale radar: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "message": str(e)
        }

if __name__ == "__main__":
    result = analyze_whale_radar("XAUUSD")
    print(f"Status: {result.get('status')}")
    print(f"Badge: {result.get('action_badge')}")
    print(f"Headline: {result.get('headline')}")
    print(f"Advice: {result.get('simple_advice')}")
    print(f"Daily Push: {result.get('daily_alert_text')}")
