import os
import sys
import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def extract_urls(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("{{ routes.collections_url }}", "/collections")
    content = content.replace("{{ routes.root_url }}", "")
    urls = re.findall(r'href="([^"#\?]+)', content)
    return set(urls)

desktop_urls = extract_urls(os.path.join(PROJECT_ROOT, "theme", "snippets", "luxury-desktop-nav.liquid"))
sidebar_urls = extract_urls(os.path.join(PROJECT_ROOT, "theme", "snippets", "luxury-sidebar-panels.liquid"))

all_urls = sorted(desktop_urls.union(sidebar_urls))
collection_urls = [u for u in all_urls if u.startswith("/collections") and u != "/collections"]
print(f"Total unique collection URLs to test: {len(collection_urls)}", flush=True)

base = "https://therareavenue.com"

def check_url(u):
    full = base + u
    req = urllib.request.Request(full, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="ignore")
            # In Prestige theme, empty collections usually say 'No products found' or 0 items, or have no product-card
            has_prods = ("product-card" in body or "product-item" in body or "card-grid" in body) and ("No products found" not in body)
            return (u, status, has_prods, None)
    except urllib.error.HTTPError as e:
        return (u, e.code, False, f"HTTPError {e.code}")
    except Exception as e:
        return (u, 0, False, str(e))

with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(check_url, collection_urls))

print("\n" + "=" * 80)
print("AUDIT RESULTS:")
print("=" * 80)

failures = []
empty = []
ok = []

for u, status, has_prods, err in results:
    if status != 200:
        failures.append((u, status, err))
        print(f"FAILED [{status}]: {u} -> {err}")
    elif not has_prods:
        empty.append(u)
        print(f"EMPTY [200]: {u} (No products found)")
    else:
        ok.append(u)
        print(f"OK [200]: {u}")

print("\n" + "=" * 80)
print(f"TOTAL OK: {len(ok)}")
print(f"TOTAL FAILED: {len(failures)}")
print(f"TOTAL EMPTY: {len(empty)}")
print("=" * 80)
