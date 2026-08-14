import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldDataFetcher")

SYMBOL_MAP = {
    "XAUUSD": "GC=F",      # COMEX Gold Futures (XAUUSD=X on yfinance returns 404)
    "FUTURES": "GC=F",      # COMEX Gold Futures
    "GLD": "GLD"            # SPDR Gold Shares ETF
}

INTERVAL_MAP = {
    "1m": {"period": "1d", "interval": "1m"},
    "5m": {"period": "5d", "interval": "5m"},
    "15m": {"period": "5d", "interval": "15m"},
    "1h": {"period": "1mo", "interval": "1h"},
    "4h": {"period": "3mo", "interval": "1h"},  # Resampled from 1h
    "1d": {"period": "2y", "interval": "1d"}
}

def generate_mock_gold_data(interval="1h", count=200):
    """Generate realistic synthetic Gold OHLCV data if live feed is unreachable."""
    now = datetime.utcnow()
    timestamps = []
    
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
    price = 4450.0  # Base realistic gold price ($/oz)
    data = []

    np.random.seed(42)

    for i in range(count):
        curr_time += step
        # Skip weekends for realistic chart gap simulation
        if curr_time.weekday() >= 5 and interval in ["1d", "1h", "4h"]:
            continue
            
        pct_change = np.random.normal(0.0002, 0.002) # slight upward trend bias
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
    """
    ticker_symbol = SYMBOL_MAP.get(symbol_key.upper(), "GC=F")
    cfg = INTERVAL_MAP.get(interval, INTERVAL_MAP["1h"])
    
    logger.info(f"Fetching gold data for ticker {ticker_symbol} with interval {interval}...")

    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=cfg["period"], interval=cfg["interval"])
        
        if df is None or df.empty or len(df) < 10:
            logger.warning("yfinance returned empty or insufficient data, switching to fallback data generator...")
            return generate_mock_gold_data(interval=interval)

        df = df.reset_index()
        
        # Standardize timestamp column name
        date_col = 'Datetime' if 'Datetime' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0])
        df = df.rename(columns={
            date_col: 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Keep relevant columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()

        # Handle 4h timeframe by resampling 1h data
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

        # Format timestamp strings
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        logger.info(f"Successfully loaded {len(df)} candles for {ticker_symbol}")
        return df

    except Exception as e:
        logger.error(f"Error fetching live data ({e}), using fallback simulation dataset...")
        return generate_mock_gold_data(interval=interval)

if __name__ == "__main__":
    df = get_gold_candles("XAUUSD", "1h")
    print(df.tail())
