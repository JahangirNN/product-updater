import httpx
import re

r = httpx.get('https://therareavenue.com/', timeout=30, follow_redirects=True)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

pattern = re.compile(r'id=["\']shopify-section-template--\d+__([^"\']+)["\']')
matches = pattern.findall(r.text)
print("Rendered section IDs in order:")
for i, sec in enumerate(matches, 1):
    print(f"  {i:2d}. {sec}")
