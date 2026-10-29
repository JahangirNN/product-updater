import urllib.request
import re

req = urllib.request.Request('https://therareavenue.com/', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8')

print(f"Total HTML size: {len(html)} bytes")

# Find all section IDs
section_matches = re.findall(r'<div id="(shopify-section-template--[^"]+)"', html)
print(f"Found {len(section_matches)} template sections:")
for sm in section_matches:
    print(f"  {sm}")

# Check featured-collections-2 HTML
fc2_pos = html.find('featured-collections-2')
if fc2_pos != -1:
    snippet = html[fc2_pos:fc2_pos+2000]
    print("\n--- featured-collections-2 snippet ---")
    print(snippet[:1500])
else:
    print("\nfeatured-collections-2 not found directly by name")
