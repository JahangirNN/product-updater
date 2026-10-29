import requests

r = requests.get("https://therareavenue.com/collections/watches", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
lines = r.text.splitlines()
for i, l in enumerate(lines):
    if "window.location.replace" in l:
        for j in range(max(0, i - 15), min(len(lines), i + 15)):
            print(f"{j:4}: {lines[j]}")
        break
