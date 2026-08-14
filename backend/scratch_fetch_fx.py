import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

js_url = 'https://mobile.firstbank.com.tw/c1/cheetah/main-VUSTP4N6.js'
js = urllib.request.urlopen(urllib.request.Request(js_url, headers={'User-Agent': 'Mozilla/5.0'}), context=ctx).read().decode('utf-8', errors='ignore')

idx = 0
while True:
    pos = js.find('ntd-currency', idx)
    if pos == -1:
        break
    snippet = js[max(0, pos-100):min(len(js), pos+200)]
    print("MATCH:", snippet)
    idx = pos + 12
