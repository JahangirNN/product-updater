import httpx
import re

client = httpx.Client(follow_redirects=True, timeout=15.0)

r = client.get("https://therareavenue.com/collections/womens-handbags/coach")
m = re.findall(r'id="shopify-section-template--29325263405222__main"[\s\S]*?</section>', r.text)
if m:
    sec = m[0]
    # strip style
    clean_sec = re.sub(r'<style>[\s\S]*?</style>', '', sec)
    pos = clean_sec.find("collection-toolbar__products-count")
    if pos != -1:
        print(clean_sec[pos:pos+2000])
    else:
        print(clean_sec[3500:5500])
else:
    print("Section not found. Full text search for 'empty':")
    for line in r.text.split("\n"):
        if "empty" in line.lower() or "filter" in line.lower() or "count" in line.lower():
            print("  ", line.strip()[:100])
