import urllib.request
import json
import ssl
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldDataFetcher")

SYMBOL_MAP = {
    "XAUUSD": "SPOT",
    "SPOT": "SPOT",
    "FUTURES": "GC=F",
    "GC=F": "GC=F",
    "GLD": "GLD"
}

INTERVAL_MAP = {
    "1m": {"period": "1d", "interval": "1m", "binance": "1m", "limit": 200},
    "5m": {"period": "5d", "interval": "5m", "binance": "5m", "limit": 200},
    "15m": {"period": "5d", "interval": "15m", "binance": "15m", "limit": 200},
    "1h": {"period": "1mo", "interval": "1h", "binance": "1h", "limit": 300},
    "4h": {"period": "3mo", "interval": "1h", "binance": "4h", "limit": 300},
    "1d": {"period": "2y", "interval": "1d", "binance": "1d", "limit": 365}
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_binance_spot_gold(interval="1h", limit=200):
    """
    Fetches real-time 24/7 physical gold spot (PAXG/USDT, 1:1 London Fine Gold 1 oz) candles from Binance.
    """
    b_interval = INTERVAL_MAP.get(interval, {}).get("binance", "1h")
    b_limit = INTERVAL_MAP.get(interval, {}).get("limit", limit)
    url = f"https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={b_interval}&limit={b_limit}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    res = urllib.request.urlopen(req, context=ctx, timeout=6)
    raw = json.loads(res.read().decode('utf-8'))
    
    data = []
    for k in raw:
        dt = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc).replace(tzinfo=None)
        data.append({
            "timestamp": dt,
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5])
        })
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def generate_mock_gold_data(interval="1h", count=200):
    """Generate realistic synthetic Gold OHLCV data if live feed is unreachable."""
    now = datetime.utcnow()
    
    if interval == "1m":
        step = timedelta(minutes=1)
    elif interval == "5m":
        step = timedelta(minutes=5)
    elif interval == "15m":
        step = timedelta(minutes=15)
    elif interval == "1h" or interval == "4h":
        step = timedelta(hours=1 if interval == "1h" else 4)
    else:
        step = timedelta(days=1)

    curr_time = now - (step * count)
    price = 4533.80  # Base realistic spot gold price ($/oz)
    data = []

    np.random.seed(42)

    for i in range(count):
        curr_time += step
        if curr_time.weekday() >= 5 and interval in ["1d", "1h", "4h"]:
            continue
            
        pct_change = np.random.normal(0.0002, 0.002)
        close_price = max(1000.0, price * (1 + pct_change))
        high_price = max(price, close_price) + abs(np.random.normal(1.5, 1.0))
        low_price = min(price, close_price) - abs(np.random.normal(1.5, 1.0))
        open_price = price
        volume = int(np.random.uniform(1500, 12000))

        data.append({
            "timestamp": curr_time.strftime("%Y-%m-%d %H:%M:%S"),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })
        price = close_price

    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def get_gold_candles(symbol_key="XAUUSD", interval="1h"):
    """
    Fetch OHLCV candles for Gold. Returns pandas DataFrame with timestamp, open, high, low, close, volume.
    Defaults to 24/7 Spot Gold (PAXG/XAUUSD).
    """
    sym = symbol_key.upper()
    cfg = INTERVAL_MAP.get(interval, INTERVAL_MAP["1h"])
    
    # 1. For Spot Gold (XAUUSD / SPOT), use real-time spot candles
    if sym in ["XAUUSD", "SPOT", "XAU"]:
        try:
            df = fetch_binance_spot_gold(interval=interval)
            if df is not None and not df.empty and len(df) >= 5:
                logger.info(f"Loaded {len(df)} spot gold candles from Binance PAXGUSDT ({interval})")
                return df
        except Exception as e:
            logger.warning(f"Binance spot fetch failed ({e}), trying yfinance PAXG-USD fallback...")

        try:
            ticker = yf.Ticker("PAXG-USD")
            df = ticker.history(period=cfg["period"], interval=cfg["interval"])
            if df is not None and not df.empty and len(df) >= 5:
                df = df.reset_index()
                date_col = 'Datetime' if 'Datetime' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0])
                df = df.rename(columns={
                    date_col: 'timestamp',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
                return df
        except Exception as e:
            logger.warning(f"yfinance PAXG-USD fallback failed ({e})...")

    # 2. For Futures (GC=F / FUTURES) or general fallback
    ticker_symbol = SYMBOL_MAP.get(sym, "GC=F")
    logger.info(f"Fetching gold data for ticker {ticker_symbol} with interval {interval}...")

    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=cfg["period"], interval=cfg["interval"])
        
        if df is None or df.empty or len(df) < 10:
            logger.warning("yfinance returned empty or insufficient data, switching to fallback data generator...")
            return generate_mock_gold_data(interval=interval)

        df = df.reset_index()
        
        date_col = 'Datetime' if 'Datetime' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0])
        df = df.rename(columns={
            date_col: 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()

        if interval == "4h":
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            resampled = df.resample('4h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna().reset_index()
            df = resampled

        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
        return df

    except Exception as e:
        logger.error(f"Error fetching live data ({e}), using fallback simulation dataset...")
        return generate_mock_gold_data(interval=interval)

if __name__ == "__main__":
    df = get_gold_candles("XAUUSD", "1h")
    print(df.tail())

