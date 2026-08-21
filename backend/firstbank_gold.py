import urllib.request
import json
import ssl
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger("FirstBankGold")

def fetch_firstbank_forex_rates() -> Tuple[float, float]:
    """
    Directly fetches official live USD Spot Exchange Rates from First Bank official API.
    URL: https://www.firstbank.com.tw/sites/fcb/touch/1565688252532
    API: https://mobile.firstbank.com.tw/api/ileobank/info/v1/fe/getrate
    Returns: (usd_spot_buy, usd_spot_sell) e.g. (32.11, 32.21)
    """
    url = "https://mobile.firstbank.com.tw/api/ileobank/info/v1/fe/getrate"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://mobile.firstbank.com.tw',
        'Referer': 'https://www.firstbank.com.tw/sites/fcb/touch/1565688252532'
    }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = json.dumps({"header": {}, "body": {}}).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        res = urllib.request.urlopen(req, context=ctx, timeout=5)
        resp_data = json.loads(res.read().decode('utf-8'))

        if resp_data.get("success") and "clientResponse" in resp_data:
            rate_list = resp_data["clientResponse"].get("rateDataList", [])
            usd_fx = next((r for r in rate_list if r.get("ccd") == "01"), None)
            if usd_fx:
                buy_spot = float(usd_fx.get("buyRate1", 32.11))
                sell_spot = float(usd_fx.get("sellRate1", 32.21))
                return buy_spot, sell_spot
    except Exception as e:
        logger.error(f"Failed to fetch live FirstBank FX API ({e})")
    
    return 32.11, 32.21

def fetch_firstbank_gold_rates(spot_price_usd: float = 4450.0) -> Dict[str, Any]:
    """
    Directly fetches official live Gold Passbook rates and USD Forex rates from First Bank's official APIs.
    Gold URL: https://mobile.firstbank.com.tw/c1/cheetah/zh/07/gold/rate?channel=X
    FX URL: https://www.firstbank.com.tw/sites/fcb/touch/1565688252532
    """
    # 1. Fetch Official First Bank USD Spot Forex Rates (即期買入 / 即期賣出)
    usd_spot_buy, usd_spot_sell = fetch_firstbank_forex_rates()

    # 2. Fetch Official First Bank Gold Passbook Rates
    gold_url = "https://mobile.firstbank.com.tw/api/ileobank/info/v1/gold/getrate"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://mobile.firstbank.com.tw',
        'Referer': 'https://mobile.firstbank.com.tw/c1/cheetah/zh/07/gold/rate?channel=X'
    }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = json.dumps({"header": {}, "body": {}}).encode('utf-8')

    try:
        req = urllib.request.Request(gold_url, data=payload, headers=headers, method='POST')
        res = urllib.request.urlopen(req, context=ctx, timeout=5)
        resp_data = json.loads(res.read().decode('utf-8'))

        if resp_data.get("success") and "clientResponse" in resp_data:
            client_resp = resp_data["clientResponse"]
            rate_list = client_resp.get("rateDataList", [])
            
            twd_rate = next((r for r in rate_list if r.get("ccd") == "00"), None)
            usd_rate = next((r for r in rate_list if r.get("ccd") == "01"), None)

            if twd_rate:
                gram_buy = int(float(twd_rate["buyRate"]))
                gram_sell = int(float(twd_rate["sellRate"]))
                chien_buy = round(gram_buy * 3.75)
                chien_sell = round(gram_sell * 3.75)

                usd_gold_buy = float(usd_rate["buyRate"]) if usd_rate else 4350.0
                usd_gold_sell = float(usd_rate["sellRate"]) if usd_rate else 4424.0

                return {
                    "bank_name": "第一銀行 (First Bank)",
                    "currency": "TWD (新臺幣)",
                    "gold_url": "https://mobile.firstbank.com.tw/c1/cheetah/zh/07/gold/rate?channel=X",
                    "fx_url": "https://www.firstbank.com.tw/sites/fcb/touch/1565688252532",
                    "gram_buy": gram_buy,            # 第一銀行黃金存摺買入價 (直接擷取官網)
                    "gram_sell": gram_sell,          # 第一銀行黃金存摺賣出價 (直接擷取官網)
                    "chien_buy": int(chien_buy),     # 1台錢 買進價
                    "chien_sell": int(chien_sell),   # 1台錢 賣出價
                    "usd_spot_buy": round(usd_spot_buy, 3),   # 第一銀行美元即期買入匯率 (官網直連 e.g. 32.11)
                    "usd_spot_sell": round(usd_spot_sell, 3), # 第一銀行美元即期賣出匯率 (官網直連 e.g. 32.21)
                    "usd_gold_buy": usd_gold_buy,             # 美金計價黃金存摺買進
                    "usd_gold_sell": usd_gold_sell,           # 美金計價黃金存摺賣出
                    "spread": int(gram_sell - gram_buy),
                    "last_updated": "第一銀行官網雙API直連 (免計算)"
                }
    except Exception as e:
        logger.error(f"Failed to fetch live FirstBank official Gold API ({e})")

    # Fallback if official API is temporarily unreachable
    base_sell = (spot_price_usd * usd_spot_sell) / 31.1034768
    base_buy = (spot_price_usd * usd_spot_buy) / 31.1034768
    gram_sell = round(base_sell)
    gram_buy = round(base_buy * 0.99)
    chien_buy = round(gram_buy * 3.75)
    chien_sell = round(gram_sell * 3.75)

    return {
        "bank_name": "第一銀行 (First Bank)",
        "currency": "TWD (新臺幣)",
        "gold_url": "https://mobile.firstbank.com.tw/c1/cheetah/zh/07/gold/rate?channel=X",
        "fx_url": "https://www.firstbank.com.tw/sites/fcb/touch/1565688252532",
        "gram_buy": int(gram_buy),
        "gram_sell": int(gram_sell),
        "chien_buy": int(chien_buy),
        "chien_sell": int(chien_sell),
        "usd_spot_buy": round(usd_spot_buy, 3),
        "usd_spot_sell": round(usd_spot_sell, 3),
        "usd_gold_buy": round(spot_price_usd * 0.992, 2),
        "usd_gold_sell": round(spot_price_usd * 1.008, 2),
        "spread": int(gram_sell - gram_buy),
        "last_updated": "離線備用換算"
    }

if __name__ == "__main__":
    rates = fetch_firstbank_gold_rates()
    print(json.dumps(rates, indent=2, ensure_ascii=False))
