import re
import html

def extract_urls(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Normalize collections url
    content = content.replace("{{ routes.collections_url }}", "/collections")
    # match href="..."
    raw_urls = re.findall(r'href=["\']([^"\']+)["\']', content)
    clean = set()
    for u in raw_urls:
        u = html.unescape(u.strip())
        if u.startswith("/") and not u.startswith("/#"):
            clean.add(u)
    return sorted(list(clean))

desktop_urls = extract_urls("theme/snippets/luxury-desktop-nav.liquid")
sidebar_urls = extract_urls("theme/snippets/luxury-sidebar-panels.liquid")

print("--- DESKTOP URLS (count = {}) ---".format(len(desktop_urls)))
for u in desktop_urls:
    print(u)

print("\n--- SIDEBAR URLS (count = {}) ---".format(len(sidebar_urls)))
for u in sidebar_urls:
    print(u)
