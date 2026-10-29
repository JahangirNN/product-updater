import urllib.request
import re

url = 'https://therareavenue.com/collections/men'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8')
    inputs = re.findall(r'<input[^>]*name="filter\.p\.vendor"[^>]*>', html)
    for inp in inputs[:10]:
        print(inp)
