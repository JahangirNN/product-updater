import time
import json
import re
from curl_cffi import requests

urls = [
    "https://www.sephora.com/product/summer-fridays-lip-butter-balm-P455936",
    "https://www.sephora.com/product/summer-fridays-flushed-lip-stain-P520759",
    "https://www.sephora.com/product/hol26-holiday-trio-marshmallow-mini-P526100",
    "https://www.sephora.com/product/hol26-lip-butter-balm-minis-pinks-set-P526164",
    "https://www.sephora.com/product/summer-fridays-jet-lag-tm-eye-patches-P515210",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

session = requests.Session(impersonate="chrome124")
print("Benchmarking session reuse + fast regex parsing:")

for idx, url in enumerate(urls, 1):
    t0 = time.perf_counter()
    r = session.get(url, headers=headers, timeout=20)
    dur_net = time.perf_counter() - t0
    
    t1 = time.perf_counter()
    # Fast regex
    m = re.search(r'<script[^>]*>(\{"page":\{"product":.*?)</script>', r.text, re.DOTALL)
    pdata = None
    if m:
        try:
            parsed = json.loads(m.group(1))
            pdata = parsed.get("page", {}).get("product")
        except Exception:
            pass
    dur_parse = time.perf_counter() - t1
    
    total_dur = time.perf_counter() - t0
    has_pdata = bool(pdata)
    print(f"[{idx}] Net: {dur_net:.2f}s | Parse: {dur_parse*1000:.1f}ms | Total: {total_dur:.2f}s | Success: {has_pdata}")
