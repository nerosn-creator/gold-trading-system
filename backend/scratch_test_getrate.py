import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://mobile.firstbank.com.tw/api/ileobank/info/v1/gold/getrate'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json;charset=UTF-8',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://mobile.firstbank.com.tw',
    'Referer': 'https://mobile.firstbank.com.tw/c1/cheetah/zh/07/gold/rate?channel=X'
}

# Try different payload structures
payloads = [
    {},
    {"data": {}},
    {"body": {}},
    {"request": {}},
    {"header": {}, "body": {}}
]

for i, p in enumerate(payloads):
    try:
        data_bytes = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        res = urllib.request.urlopen(req, context=ctx, timeout=5)
        res_text = res.read().decode('utf-8')
        print(f"Payload {i}: Status {res.status} -> {res_text[:300]}")
    except Exception as e:
        print(f"Payload {i} Error: {e}")
