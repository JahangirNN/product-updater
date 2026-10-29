import urllib.request
import re

def inspect_details(url):
    print("=" * 70)
    print(f"URL: {url}")
    print("=" * 70)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req) as resp:
        page_html = resp.read().decode('utf-8', errors='ignore')
    
    # Search header
    header_m = re.search(r'<div class="section-header[^"]*">(.*?)</div>\s*</div>', page_html, re.DOTALL)
    if header_m:
        clean = re.sub(r'<[^>]+>', ' ', header_m.group(1))
        print("Header text:", ' '.join(clean.split()))
        
    # Product titles
    titles = re.findall(r'<a[^>]+href="(/products/[^"]+)"[^>]*>([^<]+)</a>', page_html)
    print(f"Product links count: {len(titles)}")
    for href, t in titles[:6]:
        print(f"  - {t.strip()} ({href})")
        
    # Look for active facets
    active_m = re.findall(r'class="removable-facet[^"]*"[\s\S]*?</div>', page_html)
    print(f"Active facets HTML blocks: {len(active_m)}")
    for a in active_m:
        print("    ", re.sub(r'<[^>]+>', ' ', a).strip())

    # Look at filters in the page
    filter_sections = re.findall(r'<accordion-disclosure[^>]*>[\s\S]*?</accordion-disclosure>', page_html)
    for f in filter_sections:
        sum_m = re.search(r'<summary[^>]*>([\s\S]*?)</summary>', f)
        if sum_m:
            title = re.sub(r'<[^>]+>', '', sum_m.group(1)).strip()
            if any(k in title.lower() for k in ['brand', 'avail', 'price', 'silhouette', 'vendor', 'type']):
                inputs = re.findall(r'<input[^>]+name="([^"]+)"[^>]*value="([^"]*)"', f)
                print(f"  Filter section: '{title}', inputs: {inputs[:5]}")

if __name__ == '__main__':
    inspect_details('https://therareavenue.com/search?q=Wallet')
    inspect_details('https://therareavenue.com/search?q=Wallet&filter.p.vendor=COACH')
