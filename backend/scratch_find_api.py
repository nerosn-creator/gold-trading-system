import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

js_url = 'https://mobile.firstbank.com.tw/c1/cheetah/chunk-UA2IYLCD.js'
js_content = urllib.request.urlopen(urllib.request.Request(js_url, headers={'User-Agent': 'Mozilla/5.0'}), context=ctx).read().decode('utf-8', errors='ignore')

matches = [m.start() for m in re.finditer(r'\.getRate\(', js_content)]
for m in matches:
    print("--- CALL MATCH AT", m, "---")
    print(js_content[max(0, m-200):min(len(js_content), m+300)])
