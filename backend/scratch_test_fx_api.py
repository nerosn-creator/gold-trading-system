import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url_fe = 'https://mobile.firstbank.com.tw/api/ileobank/info/v1/fe/getrate'
url_usd = 'https://mobile.firstbank.com.tw/api/ileobank/info/v1/fe/getusdrate'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json;charset=UTF-8',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://mobile.firstbank.com.tw',
    'Referer': 'https://mobile.firstbank.com.tw/c1/cheetah/zh/07/currency?channel=X'
}

payload = json.dumps({"header": {}, "body": {}}).encode('utf-8')

print("--- Testing /api/ileobank/info/v1/fe/getrate ---")
try:
    req = urllib.request.Request(url_fe, data=payload, headers=headers, method='POST')
    res = urllib.request.urlopen(req, context=ctx, timeout=5)
    resp = json.loads(res.read().decode('utf-8'))
    print("FE GetRate Success:", resp.get("success"))
    if resp.get("success"):
        print(json.dumps(resp.get("clientResponse"), indent=2, ensure_ascii=False)[:1000])
except Exception as e:
    print("FE Error:", e)

print("\n--- Testing /api/ileobank/info/v1/fe/getusdrate ---")
try:
    req = urllib.request.Request(url_usd, data=payload, headers=headers, method='POST')
    res = urllib.request.urlopen(req, context=ctx, timeout=5)
    resp = json.loads(res.read().decode('utf-8'))
    print("USD GetRate Success:", resp.get("success"))
    if resp.get("success"):
        print(json.dumps(resp.get("clientResponse"), indent=2, ensure_ascii=False)[:1000])
except Exception as e:
    print("USD Error:", e)
