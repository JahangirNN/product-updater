import urllib.request
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://therareavenue.com/search?q=Wallet'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Find price accordion
m = re.findall(r'<accordion-disclosure[^>]*>[\s\S]*?</accordion-disclosure>', html)
for a in m:
    if 'Price' in a:
        print("=== Price accordion HTML ===")
        print(a[:1000])
        print("============================")
