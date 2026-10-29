import os
import sys
import urllib.request
import urllib.error

pairs = [
    ("/collections/all/hoka", "/collections/hoka"),
    ("/collections/all/on", "/collections/on-running"),
    ("/collections/all/salomon", "/collections/salomon"),
    ("/collections/all/asics", "/collections/asics"),
    ("/collections/all/nike", "/collections/nike"),
    ("/collections/all/adidas", "/collections/adidas"),
]

for tag_url, col_url in pairs:
    for u in [tag_url, col_url]:
        try:
            req = urllib.request.Request("https://therareavenue.com" + u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                has_prods = ("product-card" in html or "product-item" in html) and ("No products found" not in html)
                print(f"[{resp.status}] {u} -> Has Products: {has_prods}")
        except Exception as e:
            print(f"[ERR] {u}: {e}")
        import time; time.sleep(0.5)
