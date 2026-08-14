import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://mobile.firstbank.com.tw/api/ileobank/info/v1/gold/getrate'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*'
}

data = json.dumps({}).encode('utf-8')

# Try POST
print("--- Trying POST ---")
try:
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    res = urllib.request.urlopen(req, context=ctx, timeout=10)
    print("Status:", res.status)
    body = res.read().decode('utf-8')
    print("Body:", body)
except Exception as e:
    print("POST Error:", e)

# Try GET
print("\n--- Trying GET ---")
try:
    req = urllib.request.Request(url, headers=headers, method='GET')
    res = urllib.request.urlopen(req, context=ctx, timeout=10)
    print("Status:", res.status)
    body = res.read().decode('utf-8')
    print("Body:", body)
except Exception as e:
    print("GET Error:", e)
