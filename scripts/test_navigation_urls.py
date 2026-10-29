import os
import sys
import re
import httpx

STORE_URL = "https://therareavenue.com"

# Let's extract all hrefs from both snippets
DESKTOP_SNIPPET = r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater\theme\snippets\luxury-desktop-nav.liquid"
SIDEBAR_SNIPPET = r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater\theme\snippets\luxury-sidebar-panels.liquid"

def extract_urls(filepath):
    urls = set()
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # matches {{ routes.collections_url }}/... or /collections/...
    matches = re.findall(r'href=["\'](?:\{\{\s*routes\.collections_url\s*\}\}|\/collections)([^"\']+)["\']', content)
    for m in matches:
        clean = m.strip()
        if not clean.startswith("/"):
            clean = "/" + clean
        urls.add("/collections" + clean)
    return sorted(list(urls))

desktop_urls = extract_urls(DESKTOP_SNIPPET)
sidebar_urls = extract_urls(SIDEBAR_SNIPPET)
all_urls = sorted(list(set(desktop_urls + sidebar_urls)))

print(f"Extracted {len(all_urls)} unique collection URLs from theme snippets.")

client = httpx.Client(timeout=15.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

results = []
for path in all_urls:
    full_url = f"{STORE_URL}{path}"
    try:
        r = client.get(full_url)
        status = r.status_code
        # Check if page has products or says 'No products found'
        text = r.text
        has_empty_notice = ("no products found" in text.lower() or "there are no products" in text.lower())
        results.append((path, status, has_empty_notice, len(text)))
        print(f"[{status}] {'EMPTY ' if has_empty_notice else 'OK    '} {path}")
    except Exception as e:
        results.append((path, "ERR", False, str(e)))
        print(f"[ERR] {path} -> {e}")

print("=" * 80)
print(f"TOTAL CHECKED: {len(results)}")
failed = [r for r in results if r[1] != 200 or r[2]]
if failed:
    print(f"FAILED OR EMPTY URLS ({len(failed)}):")
    for f in failed:
        print(f"  Status: {f[1]} | Empty: {f[2]} | URL: {f[0]}")
else:
    print("ALL URLS RETURNED 200 AND CONTAIN PRODUCTS!")
