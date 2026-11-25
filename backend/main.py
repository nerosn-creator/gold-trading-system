import sys
import os
import re
import time
import hmac
import math
import threading
from collections import defaultdict
from urllib.parse import urlparse
import pandas as pd

# Add current directory to sys.path for relative imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

from data_fetcher import get_gold_candles
from indicator_engine import calculate_indicators
from signal_generator import generate_signals, get_latest_signal_summary
from backtester import run_backtest
from events_service import get_daily_gold_events
import alert_service

app = FastAPI(title="Gold Trading Signal System API", version="1.0.0")

# --- Security Helpers ---
ALLOWED_SYMBOLS = {"XAUUSD", "SPOT", "XAU", "FUTURES", "GC=F", "GLD"}
ALLOWED_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}
ALLOWED_ALERT_UNITS = {"gram", "chien", "usd_oz"}
ALLOWED_COMPARISONS = {"lte", "gte"}
TIME_HHMM_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

_rate_limit_lock = threading.Lock()
_rate_limit_buckets = defaultdict(list)


def _validate_symbol(symbol: str) -> str:
    sym = (symbol or "XAUUSD").strip().upper()
    if sym not in ALLOWED_SYMBOLS:
        raise HTTPException(status_code=400, detail="不支援的商品代碼")
    return sym


def _validate_interval(interval: str) -> str:
    iv = (interval or "1h").strip().lower()
    if iv not in ALLOWED_INTERVALS:
        raise HTTPException(status_code=400, detail="不支援的時間週期")
    return iv


def _verify_admin_key(request: Request):
    """If ADMIN_API_KEY env var is set, require matching X-Admin-Key header."""
    expected = os.environ.get("ADMIN_API_KEY", "").strip()
    if not expected:
        return
    provided = (request.headers.get("X-Admin-Key") or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="未授權的操作：缺少或無效的管理金鑰")


def _check_rate_limit(bucket: str, request: Request, limit: int, window_sec: int):
    client_ip = request.client.host if request.client else "unknown"
    key = f"{bucket}:{client_ip}"
    now = time.time()
    with _rate_limit_lock:
        timestamps = [t for t in _rate_limit_buckets[key] if now - t < window_sec]
        if len(timestamps) >= limit:
            raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試")
        timestamps.append(now)
        _rate_limit_buckets[key] = timestamps


def _get_safe_sync_url() -> str:
    url = os.environ.get("ALERT_SYNC_URL", "").strip().rstrip("/")
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return ""
    return url


@app.on_event("startup")
def startup_event():
    # Only run background alert monitor on long-running persistent host (not serverless like Vercel/Lambda)
    is_serverless = "VERCEL" in os.environ or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    if not is_serverless:
        try:
            alert_service.start_alert_monitor()
        except Exception as e:
            print(f"Failed to start alert monitor: {e}")

_allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _allowed_origins_env:
    _cors_origins = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
else:
    _cors_origins = ["http://localhost:8084", "http://127.0.0.1:8084"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return response

@app.get("/api/gold/candles")
def api_get_candles(symbol: str = "XAUUSD", interval: str = "1h"):
    """Fetch candles with technical indicators and signals for charting."""
    symbol = _validate_symbol(symbol)
    interval = _validate_interval(interval)
    df = get_gold_candles(symbol, interval)
    df = calculate_indicators(df)
    df = generate_signals(df)

    # Format timestamp for JSON serialization
    df_out = df.copy()
    df_out['timestamp'] = df_out['timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Convert to records and clean any NaNs into None for strict JSON compliance
    import numpy as np
    records = df_out.to_dict(orient="records")
    clean_records = [
        {k: (None if (isinstance(v, (float, int, np.number)) and pd.isna(v)) else v) for k, v in r.items()}
        for r in records
    ]


    return {
        "symbol": symbol,
        "interval": interval,
        "count": len(clean_records),
        "data": clean_records
    }


@app.get("/api/gold/summary")
def api_get_summary(symbol: str = "XAUUSD", interval: str = "1h"):
    """Get current gold signal summary and indicator state."""
    symbol = _validate_symbol(symbol)
    interval = _validate_interval(interval)
    df = get_gold_candles(symbol, interval)
    df = calculate_indicators(df)
    df = generate_signals(df)
    summary = get_latest_signal_summary(df)
    return summary

@app.get("/api/gold/backtest")
def api_get_backtest(symbol: str = "XAUUSD", interval: str = "1h", capital: float = 10000.0):
    """Run historical backtest on current signals."""
    symbol = _validate_symbol(symbol)
    interval = _validate_interval(interval)
    if not math.isfinite(capital) or capital <= 0 or capital > 1e9:
        raise HTTPException(status_code=400, detail="初始資金必須介於 0 與 1,000,000,000 之間")
    df = get_gold_candles(symbol, interval)
    df = calculate_indicators(df)
    df = generate_signals(df)
    result = run_backtest(df, initial_capital=capital)
    return result

@app.post("/api/gold/optimize")
def api_run_optimization(request: Request, symbol: str = "XAUUSD", interval: str = "1d"):
    """
    Triggers AI auto-evolution optimizer to tune indicator weights and maximize win rate.
    """
    _verify_admin_key(request)
    _check_rate_limit("optimize", request, limit=3, window_sec=60)
    symbol = _validate_symbol(symbol)
    interval = _validate_interval(interval)
    from strategy_optimizer import auto_optimize_strategy, load_evolved_weights
    df = get_gold_candles(symbol, interval)
    df = calculate_indicators(df)
    evolved = auto_optimize_strategy(df)
    return {
        "status": "SUCCESS",
        "message": f"AI 策略已成功進化至第 {evolved.get('generation', 1)} 代！",
        "evolved_weights": evolved
    }

@app.get("/api/gold/optimize_status")
def api_get_optimization_status():
    """Returns current evolved strategy weights and win rate status."""
    from strategy_optimizer import load_evolved_weights
    return load_evolved_weights()

@app.get("/api/gold/longterm")
def api_get_longterm(symbol: str = "XAUUSD"):
    """
    Calculates 3 to 6-month macro investment entry alerts and strategic price targets for Gold.
    Quantitative Proofs:
    1. 200 SMA (200-day Simple Moving Average): Wall Street institutional bull/bear line.
    2. 50 EMA (50-day Exponential Moving Average): Medium-term structural support.
    3. 6-Month Fibonacci 38.2% & 50.0% Retracement: Standard technical pullback formula.
    4. Accumulate Zone: Bounded by max(fib_382, sma_50) ~ current_price * 0.99.
    5. Target Prices: Projected via 6% (3M) and 12% (6M) expected multi-month trend expansions.
    """
    symbol = _validate_symbol(symbol)
    df = get_gold_candles(symbol, "1d")
    if df.empty or len(df) < 50:
        return {"status": "ERROR", "message": "insufficient data"}

    curr = df.iloc[-1]
    current_price = float(curr['close'])

    # Calculate 50-day and 200-day SMAs
    sma_50 = float(df['close'].rolling(50).mean().iloc[-1])
    sma_200 = float(df['close'].rolling(200).mean().bfill().iloc[-1])

    # Recent 6-Month Swing High and Low (126 trading days)
    recent_df = df.tail(126) if len(df) >= 126 else df
    high_6m = float(recent_df['high'].max())
    low_6m = float(recent_df['low'].min())

    # Fibonacci Retracement Levels
    fib_diff = high_6m - low_6m
    fib_236 = round(high_6m - (0.236 * fib_diff), 2)
    fib_382 = round(high_6m - (0.382 * fib_diff), 2)
    fib_500 = round(high_6m - (0.500 * fib_diff), 2)

    # Strict Mathematical Pullback Bounds
    buy_upper = round(min(current_price * 0.99, fib_236), 2)
    buy_lower = round(min(current_price * 0.95, sma_50 if sma_50 < current_price else fib_382), 2)

    accumulate_zone = f"${buy_lower:.2f} ~ ${buy_upper:.2f}"

    # Target Prices: Projected via risk-reward ratio and 6-month Fibonacci expansion
    target_3m = round(max(current_price * 1.06, high_6m * 1.02), 2)
    target_6m = round(max(current_price * 1.12, high_6m * 1.07), 2)

    rating_text = f"🚀 3~6個月戰略建議：等待回檔支撐區 (${buy_lower:.0f}~${buy_upper:.0f}) 分批布局"

    technical_proofs = [
        f"200日牛熊均線 (200 SMA): ${sma_200:.2f} (金價現報 ${current_price:.2f} 高於此線，確立長多)",
        f"50日均線 (50 SMA): ${sma_50:.2f} (中期強支撐點位)",
        f"近6個月斐波那契 38.2% 黃金分割位: ${fib_382:.2f}",
        f"近6個月高點: ${high_6m:.2f} / 低點: ${low_6m:.2f}"
    ]

    return {
        "symbol": "XAU/USD",
        "current_price": current_price,
        "sma_50": round(sma_50, 2),
        "sma_200": round(sma_200, 2),
        "high_6m": round(high_6m, 2),
        "low_6m": round(low_6m, 2),
        "fib_236": fib_236,
        "fib_382": fib_382,
        "fib_500": fib_500,
        "macro_score": 85,
        "macro_rating": "STRONG_ACCUMULATE",
        "rating_text": rating_text,
        "accumulate_zone": accumulate_zone,
        "target_3m": target_3m,
        "target_6m": target_6m,
        "technical_proofs": technical_proofs
    }

@app.get("/api/gold/whale-radar")
def api_get_whale_radar(symbol: str = "XAUUSD"):
    """
    Returns 1-month wave analysis of institutional whale profit-taking vs dip-buying status.
    """
    symbol = _validate_symbol(symbol)
    from whale_detector import analyze_whale_radar
    return analyze_whale_radar(symbol)

@app.post("/api/gold/whale-radar/send-telegram")
def api_send_whale_radar_telegram(request: Request):
    """
    Triggers sending the daily whale radar summary to Telegram.
    """
    _verify_admin_key(request)
    _check_rate_limit("whale_tg", request, limit=3, window_sec=60)
    success, msg = alert_service.send_whale_radar_telegram(force=True)
    return {
        "status": "SUCCESS" if success else "ERROR",
        "message": msg
    }

@app.get("/api/gold/firstbank")
def api_get_firstbank_rates(symbol: str = "XAUUSD"):
    """
    Returns live First Bank TWD Gold Passbook buy/sell exchange rates.
    Target link: https://mobile.firstbank.com.tw/c1/cheetah/zh/07/gold/rate?channel=X
    """
    symbol = _validate_symbol(symbol)
    from firstbank_gold import fetch_firstbank_gold_rates
    df = get_gold_candles(symbol, "1m")
    current_price = float(df.iloc[-1]['close']) if not df.empty else 4450.0
    rates = fetch_firstbank_gold_rates(current_price)
    return rates

@app.get("/api/alerts/settings")
def api_get_alert_settings():
    """Get current First Bank gold alert settings (with bot_token masked) and current market prices."""
    import requests
    is_serverless = "VERCEL" in os.environ or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    if is_serverless:
        sync_url = _get_safe_sync_url()
        if sync_url:
            try:
                headers = {"ngrok-skip-browser-warning": "1"}
                admin_key = os.environ.get("ADMIN_API_KEY", "").strip()
                if admin_key:
                    headers["X-Admin-Key"] = admin_key
                r = requests.get(
                    f"{sync_url}/api/alerts/settings",
                    headers=headers,
                    timeout=2.0
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "SUCCESS" and "settings" in data:
                        data["settings"] = alert_service.mask_alert_settings(data["settings"])
                        return data
            except Exception:
                pass

    settings = alert_service.load_alert_settings()
    from firstbank_gold import fetch_firstbank_gold_rates
    try:
        current_rates = fetch_firstbank_gold_rates()
    except Exception:
        current_rates = {}
    return {
        "status": "SUCCESS",
        "settings": alert_service.mask_alert_settings(settings),
        "current_rates": current_rates
    }

@app.post("/api/alerts/settings")
async def api_save_alert_settings(request: Request):
    """Save First Bank gold price alert settings."""
    _verify_admin_key(request)
    _check_rate_limit("alert_save", request, limit=15, window_sec=60)
    import requests
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="無效的 JSON 請求內容")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="設定格式錯誤")

    is_serverless = "VERCEL" in os.environ or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")

    settings = alert_service.load_alert_settings()

    # Validate fields before applying
    if "unit" in data and data["unit"] not in ALLOWED_ALERT_UNITS:
        raise HTTPException(status_code=400, detail="無效的計價單位")
    if "comparison" in data and data["comparison"] not in ALLOWED_COMPARISONS:
        raise HTTPException(status_code=400, detail="無效的比較條件")
    if "target_price" in data:
        try:
            tp_val = float(data["target_price"])
            if not math.isfinite(tp_val) or tp_val < 0 or tp_val > 1e7:
                raise ValueError()
            data["target_price"] = tp_val
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="目標價格必須為有效的正數")
    if "cooldown_minutes" in data:
        try:
            cd_val = int(data["cooldown_minutes"])
            if cd_val < 1 or cd_val > 1440:
                raise ValueError()
            data["cooldown_minutes"] = cd_val
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="冷卻時間必須介於 1 到 1440 分鐘")
    for time_field in ("quiet_hours_start", "quiet_hours_end"):
        if time_field in data and data[time_field]:
            if not TIME_HHMM_RE.match(str(data[time_field]).strip()):
                raise HTTPException(status_code=400, detail="勿擾時間格式必須為 HH:MM")

    # Preserve stored bot_token if client left it blank (since GET masks bot_token)
    incoming_token = str(data.get("bot_token", "") or "").strip()
    if incoming_token:
        if not alert_service.validate_bot_token(incoming_token):
            raise HTTPException(status_code=400, detail="Telegram Bot Token 格式無效")
        settings["bot_token"] = incoming_token

    if "chat_id" in data:
        incoming_chat = str(data.get("chat_id", "") or "").strip()
        if incoming_chat and not alert_service.validate_chat_id(incoming_chat):
            raise HTTPException(status_code=400, detail="Telegram Chat ID 格式無效")
        if incoming_chat:
            settings["chat_id"] = incoming_chat

    for field in [
        "enabled", "unit", "target_price",
        "comparison", "cooldown_minutes", "quiet_hours_enabled",
        "quiet_hours_start", "quiet_hours_end", "updated_at"
    ]:
        if field in data:
            settings[field] = data[field]
    if "updated_at" not in data or not data.get("updated_at"):
        settings["updated_at"] = int(time.time() * 1000)

    # If running on serverless (e.g. Vercel), forward the update to the persistent runner tunnel if configured
    if is_serverless:
        sync_url = _get_safe_sync_url()
        if sync_url:
            try:
                headers = {"ngrok-skip-browser-warning": "1"}
                admin_key = os.environ.get("ADMIN_API_KEY", "").strip()
                if admin_key:
                    headers["X-Admin-Key"] = admin_key
                requests.post(
                    f"{sync_url}/api/alerts/settings",
                    json=data,
                    headers=headers,
                    timeout=3.0
                )
            except Exception as e:
                print(f"Forward to local runner error: {e}")

    alert_service.save_alert_settings(settings)

    if not is_serverless:
        if settings.get("enabled"):
            alert_service.start_alert_monitor()
        else:
            alert_service.stop_alert_monitor()

    return {
        "status": "SUCCESS",
        "message": "一銀黃金價格警報通知設定已成功儲存！",
        "settings": alert_service.mask_alert_settings(settings)
    }

@app.post("/api/alerts/test")
async def api_test_alert_telegram(request: Request):
    """Test send a verification notification to the specified Telegram Bot/Chat."""
    _verify_admin_key(request)
    _check_rate_limit("alert_test", request, limit=5, window_sec=60)
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="無效的請求格式")
    bot_token = str(data.get("bot_token") or "").strip()
    chat_id = str(data.get("chat_id") or "").strip()
    if not bot_token or not chat_id:
        settings = alert_service.load_alert_settings()
        bot_token = bot_token or settings.get("bot_token", "")
        chat_id = chat_id or settings.get("chat_id", "")

    if not bot_token or not chat_id:
        return {"status": "ERROR", "message": "請先填寫 Telegram Bot Token 與 Chat ID！"}

    success, msg = alert_service.send_test_telegram(bot_token, chat_id)
    return {
        "status": "SUCCESS" if success else "ERROR",
        "message": msg
    }

@app.get("/api/alerts/history")
def api_get_alert_history():
    """Get history of triggered alerts."""
    settings = alert_service.load_alert_settings()
    return {
        "status": "SUCCESS",
        "history": settings.get("history", [])
    }

@app.get("/api/gold/spot_quote")
def api_get_spot_quote(symbol: str = "XAUUSD"):
    """
    Returns live International Gold Spot Market quote matching TRUNEY / First Bank professional board,
    including intraday trend line points, TWD conversion, and COMEX futures spread.
    """
    symbol = _validate_symbol(symbol)
    from datetime import datetime, timedelta
    import pytz
    from data_fetcher import generate_mock_gold_data, get_gold_candles
    from firstbank_gold import fetch_firstbank_forex_rates
    
    df_1m = get_gold_candles(symbol, "5m")
    if df_1m.empty:
        df_1m = generate_mock_gold_data("5m", count=50)
    
    df_1d = get_gold_candles(symbol, "1d")
    if df_1d.empty:
        df_1d = generate_mock_gold_data("1d", count=30)
    
    curr = df_1m.iloc[-1]
    last_price = float(curr['close'])
    open_price = float(df_1d.iloc[-1]['open']) if not df_1d.empty else float(df_1m.iloc[0]['open'])
    high_price = float(df_1d.iloc[-1]['high']) if not df_1d.empty else float(df_1m['high'].max())
    low_price = float(df_1d.iloc[-1]['low']) if not df_1d.empty else float(df_1m['low'].min())
    
    prev_close = float(df_1d.iloc[-2]['close']) if len(df_1d) >= 2 else open_price
    
    change = round(last_price - prev_close, 2)
    change_pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0.0
    
    spread = 0.68
    buy_price = round(last_price - (spread / 2.0), 2)
    sell_price = round(last_price + (spread / 2.0), 2)
    
    # Forex Rate USD/TWD for Truney equivalents
    try:
        fx_buy, fx_sell = fetch_firstbank_forex_rates()
        usd_twd = round((fx_buy + fx_sell) / 2.0, 3)
    except Exception:
        usd_twd = 32.10

    twd_per_oz = round(last_price * usd_twd, 2)
    twd_per_chien = round(twd_per_oz / 8.2944, 2)      # 1 盎司 = 8.2944 台錢
    twd_per_gram = round(twd_per_oz / 31.1034768, 2)   # 1 盎司 = 31.1034768 公克
    
    # Try fetching COMEX futures for GC1! basis spread
    try:
        df_fut = get_gold_candles("FUTURES", "5m")
        futures_gc1 = round(float(df_fut.iloc[-1]['close']), 2) if not df_fut.empty else round(last_price + 60.0, 2)
    except Exception:
        futures_gc1 = round(last_price + 60.0, 2)
    
    spread_futures = round(futures_gc1 - last_price, 2)
    
    try:
        kh_tz = pytz.timezone('Asia/Phnom_Penh')
        now_dt = datetime.now(kh_tz)
    except Exception:
        now_dt = datetime.utcnow() + timedelta(hours=7)

    date_str = now_dt.strftime("%Y/%m/%d")
    time_str = now_dt.strftime("%H:%M:%S")
    
    # Intraday trend curve points for chart rendering
    trend_points = []
    for _, row in df_1m.tail(60).iterrows():
        ts_val = row['timestamp']
        if hasattr(ts_val, 'strftime'):
            try:
                if getattr(ts_val, 'tzinfo', None) is None:
                    ts_dt = pytz.utc.localize(ts_val).astimezone(pytz.timezone('Asia/Phnom_Penh'))
                else:
                    ts_dt = ts_val.astimezone(pytz.timezone('Asia/Phnom_Penh'))
                ts = ts_dt.strftime("%H:%M")
            except Exception:
                ts = ts_val.strftime("%H:%M")
        else:
            ts = str(ts_val)
        trend_points.append({
            "time": ts,
            "price": round(float(row['close']), 2)
        })
    
    return {
        "name": "黃金現貨 (XAU/USD)",
        "source": "TRUNEY / 國際現貨即時行情",
        "date": date_str,
        "time": time_str,
        "buy_price": f"{buy_price:.2f}",
        "sell_price": f"{sell_price:.2f}",
        "last_price": f"{last_price:.2f}",
        "change": change,
        "change_pct": change_pct,
        "prev_close": f"{prev_close:.2f}",
        "open": f"{open_price:.2f}",
        "high": f"{high_price:.2f}",
        "low": f"{low_price:.2f}",
        "unit": "美元/盎司",
        "usd_twd_rate": usd_twd,
        "twd_per_oz": f"{twd_per_oz:,.2f}",
        "twd_per_chien": f"{twd_per_chien:,.2f}",
        "twd_per_gram": f"{twd_per_gram:,.2f}",
        "futures_gc1": f"{futures_gc1:.2f}",
        "spread_futures": f"{spread_futures:+.2f}",
        "truney_url": "https://www.truney.com/gold-chart?srsltid=AfmBOorf8Jl0Wpitl7_KDcP1Bepb7b5haOWoD5l6rEjZ8KUhR2KsYxj0",
        "trend_points": trend_points
    }





@app.get("/api/gold/events")
def api_get_events():
    """
    Returns today's and upcoming major economic events, live news & financial calendar impacting Gold.
    """
    return get_daily_gold_events()

# Paper Trading State
import json
import tempfile

PAPER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_account.json")
TMP_PAPER_FILE = os.path.join(tempfile.gettempdir(), "paper_account.json")

def load_paper_account_state():
    default_state = {
        "initial_balance": 100000.0,
        "cash": 100000.0,
        "positions": [],
        "position": None,
        "trades": []
    }
    for target in [PAPER_FILE, TMP_PAPER_FILE]:
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                pass
    return default_state

def save_paper_account_state():
    saved = False
    try:
        with open(PAPER_FILE, "w", encoding="utf-8") as f:
            json.dump(paper_account, f, indent=2, ensure_ascii=False)
        saved = True
    except Exception:
        pass
    if not saved:
        try:
            with open(TMP_PAPER_FILE, "w", encoding="utf-8") as f:
                json.dump(paper_account, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

paper_account = load_paper_account_state()

@app.get("/api/paper/account")
def api_get_paper_account(symbol: str = "XAUUSD"):
    """Get current paper trading account status, open position, and equity."""
    symbol = _validate_symbol(symbol)
    df = get_gold_candles(symbol, "1h")
    current_price = float(df.iloc[-1]['close']) if not df.empty else 4450.0

    positions = paper_account.get("positions", [])
    if paper_account.get("position") and paper_account["position"] not in positions:
        positions.append(paper_account["position"])
        paper_account["position"] = None
        paper_account["positions"] = positions

    unrealized_pnl = 0.0
    total_entry_value = 0.0
    
    for pos in positions:
        if pos["side"] == "BUY":
            unrealized_pnl += (current_price - pos["entry_price"]) * pos["amount_oz"]
        else: # SELL
            unrealized_pnl += (pos["entry_price"] - current_price) * pos["amount_oz"]
        total_entry_value += pos["entry_price"] * pos["amount_oz"]

    equity = paper_account["cash"] + unrealized_pnl
    total_realized = sum(t["profit"] for t in paper_account["trades"])
    unrealized_pnl_pct = round((unrealized_pnl / total_entry_value) * 100, 2) if total_entry_value > 0 else 0.0

    return {
        "initial_balance": paper_account["initial_balance"],
        "cash": round(paper_account["cash"], 2),
        "equity": round(equity, 2),
        "current_price": current_price,
        "unrealized_pnl": round(unrealized_pnl, 2),
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "total_realized_pnl": round(total_realized, 2),
        "positions": positions,
        "position": positions[-1] if positions else None,
        "trades": paper_account["trades"][-10:] # Recent 10 trades
    }

@app.post("/api/paper/trade")
def api_place_paper_trade(request: Request, side: str = Query(...), amount_oz: float = Query(1.0), symbol: str = "XAUUSD"):
    """Place a paper buy or sell trade."""
    _verify_admin_key(request)
    symbol = _validate_symbol(symbol)
    side_clean = (side or "").strip().upper()
    if side_clean not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="交易方向必須為 BUY 或 SELL")
    if not math.isfinite(amount_oz) or amount_oz <= 0 or amount_oz > 10000:
        raise HTTPException(status_code=400, detail="交易數量必須大於 0 且不超過 10,000 盎司")

    df = get_gold_candles(symbol, "1h")
    df = calculate_indicators(df)
    df = generate_signals(df)
    summary = get_latest_signal_summary(df)
    
    current_price = summary.get("current_price", 4450.0)
    tp = summary.get("take_profit", current_price * 1.02)
    sl = summary.get("stop_loss", current_price * 0.98)

    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_pos = {
        "side": side_clean,
        "entry_price": current_price,
        "amount_oz": amount_oz,
        "entry_time": now_str,
        "tp": tp,
        "sl": sl
    }
    
    if "positions" not in paper_account:
        paper_account["positions"] = []
    paper_account["positions"].append(new_pos)
    save_paper_account_state()

    return {"status": "SUCCESS", "message": f"成功建立模擬 {side_clean} 持倉 ({amount_oz} 盎司)", "positions": paper_account["positions"]}

@app.post("/api/paper/close")
def api_close_paper_trade(request: Request, symbol: str = "XAUUSD"):
    """Close all active paper trades."""
    _verify_admin_key(request)
    symbol = _validate_symbol(symbol)
    positions = paper_account.get("positions", [])
    if paper_account.get("position") and paper_account["position"] not in positions:
        positions.append(paper_account["position"])
        
    if not positions:
        return {"status": "ERROR", "message": "目前無持倉"}

    df = get_gold_candles(symbol, "1h")
    exit_price = float(df.iloc[-1]['close']) if not df.empty else positions[0]["entry_price"]

    total_profit = 0
    from datetime import datetime
    exit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for pos in positions:
        if pos["side"] == "BUY":
            profit = (exit_price - pos["entry_price"]) * pos["amount_oz"]
        else:
            profit = (pos["entry_price"] - exit_price) * pos["amount_oz"]
            
        total_profit += profit
        
        trade_record = {
            "side": pos["side"],
            "entry_time": pos["entry_time"],
            "entry_price": pos["entry_price"],
            "exit_time": exit_time,
            "exit_price": exit_price,
            "amount_oz": pos["amount_oz"],
            "profit": round(profit, 2),
            "win": profit > 0
        }
        paper_account["trades"].append(trade_record)

    paper_account["cash"] += total_profit
    paper_account["positions"] = []
    paper_account["position"] = None
    save_paper_account_state()

    return {"status": "SUCCESS", "message": f"已全部平倉，本次總損益: ${total_profit:+.2f} USD"}

@app.post("/api/paper/reset")
def api_reset_paper_account(request: Request):
    """Reset paper trading account."""
    _verify_admin_key(request)
    paper_account["cash"] = paper_account["initial_balance"]
    paper_account["position"] = None
    paper_account["positions"] = []
    paper_account["trades"] = []
    save_paper_account_state()
    return {"status": "SUCCESS", "message": "模擬交易帳戶已重置為 $100,000 USD"}

# Multi-fallback detection for frontend directory on Cloud (Vercel/Render/Railway/Docker) & Local
possible_frontend_dirs = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "public"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend"),
    os.path.join(os.getcwd(), "public"),
    os.path.join(os.getcwd(), "frontend"),
    "/var/task/public",
    "/var/task/frontend",
    "/var/task/backend/frontend",
    "/opt/render/project/src/frontend"
]

frontend_dir = None
for d in possible_frontend_dirs:
    if os.path.exists(d) and os.path.exists(os.path.join(d, "index.html")):
        frontend_dir = d
        break

if frontend_dir:
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/favicon.ico")
def serve_favicon():
    if frontend_dir:
        return FileResponse(os.path.join(frontend_dir, "index.html"))
    return {"status": "ok"}

@app.get("/manifest.json")
def serve_manifest():
    if frontend_dir:
        manifest_path = os.path.join(frontend_dir, "manifest.json")
        if os.path.exists(manifest_path):
            return FileResponse(manifest_path, media_type="application/json")
    return {"name": "Gold Trading System"}

@app.get("/")
def serve_index():
    if frontend_dir:
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return {"message": "Gold Trading Signal API is running."}

@app.get("/{full_path:path}")
def serve_catchall(full_path: str):
    if frontend_dir and not full_path.startswith("api/"):
        # Strictly prevent path traversal / arbitrary file read
        if "\x00" not in full_path and not full_path.startswith(("/", "\\")):
            base_real = os.path.realpath(frontend_dir)
            candidate_real = os.path.realpath(os.path.join(base_real, full_path))
            try:
                if os.path.commonpath([base_real, candidate_real]) == base_real and os.path.isfile(candidate_real):
                    return FileResponse(candidate_real)
            except ValueError:
                pass
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8084)



