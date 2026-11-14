import time
import json
import threading
from curl_cffi import requests

thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session(impersonate="chrome124")
    return thread_local.session

url = "https://www.sephora.com/product/summer-fridays-lip-butter-balm-P455936"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

print("Testing thread-local session reuse:")
s = get_session()
for i in range(3):
    t0 = time.perf_counter()
    r = s.get(url, headers=headers, timeout=20)
    dur = time.perf_counter() - t0
    print(f"Request {i+1}: {dur:.3f}s (status {r.status_code}, len={len(r.text)})")
