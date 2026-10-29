import requests

headers = {"User-Agent": "Mozilla/5.0"}

for url in ["https://therareavenue.com/collections/watches", "https://therareavenue.com/collections/accessories"]:
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=False)
        print(f"URL: {url}")
        print(f"  Status: {r.status_code}")
        has_meta = 'http-equiv="refresh"' in r.text.lower()
        print(f"  Has meta refresh? {has_meta}")
        if has_meta:
            for line in r.text.splitlines():
                if 'http-equiv="refresh"' in line.lower():
                    print(f"    Line: {line.strip()}")
        print(f"  Has redirect script? {'window.location.replace' in r.text}")
    except Exception as e:
        print(f"Error {url}: {e}")
