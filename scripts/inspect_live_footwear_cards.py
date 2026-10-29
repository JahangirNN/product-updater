import urllib.request
import re

req = urllib.request.Request('https://therareavenue.com/', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as r:
    html = r.read().decode('utf-8')

for tag in ['PERFORMANCE FOOTWEAR', 'ON RUNNING', 'HOKA']:
    idx = html.find(tag)
    if idx != -1:
        start = max(0, idx - 400)
        end = min(len(html), idx + 200)
        print(f"=== Context for {tag} ===")
        print(html[start:end])
        print("\n" + "="*50 + "\n")
    else:
        print(f"Tag {tag} not found in HTML!")
