import httpx
import re

client = httpx.Client(follow_redirects=True, timeout=15.0)

r = client.get("https://therareavenue.com/collections/womens-handbags?filter.p.vendor=COACH")
print("Status:", r.status_code)
# find all hrefs to /products/
links = re.findall(r'href="(/products/[^"]+)"', r.text)
print("Unique product links found on Coach collection page:", len(set(links)))
for l in list(set(links))[:5]:
    print("  ", l)
    # Let's test GET on this link
    pr = client.get("https://therareavenue.com" + l)
    print("   -> Status:", pr.status_code)
