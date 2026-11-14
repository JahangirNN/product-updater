import time
from concurrent.futures import ThreadPoolExecutor
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

def test_fetch(url):
    try:
        # Use Session per thread
        session = requests.Session(impersonate="chrome124")
        r = session.get(url, headers=headers, timeout=20)
        has_skus = "regularChildSkus" in r.text
        return url, r.status_code, len(r.text), has_skus, None
    except Exception as e:
        return url, 0, 0, False, str(e)

print("Testing ThreadPoolExecutor with 3 workers and requests.Session:")
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(test_fetch, u) for u in urls]
    for f in futures:
        url, status, length, has_skus, err = f.result()
        print(f"Status {status} | Length: {length} | Skus: {has_skus} | Error: {err} | {url[-30:]}")
