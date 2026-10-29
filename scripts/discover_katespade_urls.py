import asyncio
import json
import os
import re
import time
from camoufox.async_api import AsyncCamoufox

SEARCH_URL = "https://www.katespadeoutlet.com/search?q=Handbags&pmin=58&pmax=200"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "katespade_discovered_urls.json")

async def discover_urls():
    print(f"Starting Kate Spade URL Discovery on: {SEARCH_URL}")
    start_time = time.time()
    
    discovered_urls = set()
    
    async with AsyncCamoufox(headless=True) as browser:
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
        )
        page = await context.new_page()
        
        print("Navigating to search page...")
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        
        # Check initial title and total results count text
        title = await page.title()
        print(f"Page title: {title}")
        
        # Try to find total count element
        count_text = await page.evaluate('''() => {
            const el = document.querySelector('[data-qa="plp-search-result-count"], .results-count, .search-result-count');
            return el ? el.innerText : '';
        }''')
        print(f"Results counter text: {count_text}")
        
        stagnant_cycles = 0
        last_count = 0
        iteration = 0
        
        while stagnant_cycles < 8:
            iteration += 1
            
            # Extract all product URLs currently in the DOM
            current_urls = await page.evaluate('''() => {
                const anchors = Array.from(document.querySelectorAll('a[href*="/products/"]'));
                return anchors.map(a => a.href.split('?')[0]).filter(href => href.endsWith('.html'));
            }''')
            
            for u in current_urls:
                discovered_urls.add(u)
                
            count = len(discovered_urls)
            print(f"[Cycle {iteration}] Total unique products discovered so far: {count}")
            
            if count > last_count:
                stagnant_cycles = 0
                last_count = count
            else:
                stagnant_cycles += 1
                
            # If we reached 429+ products, we are good!
            if count >= 429:
                print(f"Target count reached ({count} >= 429)!")
                break
                
            # Check for "Show More" / "Load More" button
            button_clicked = await page.evaluate('''() => {
                const buttons = Array.from(document.querySelectorAll('button, a'));
                for (const b of buttons) {
                    const txt = (b.innerText || '').toLowerCase().trim();
                    if (txt.includes('show more') || txt.includes('load more') || txt.includes('view more')) {
                        b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        b.click();
                        return txt;
                    }
                }
                return null;
            }''')
            
            if button_clicked:
                print(f"  Clicked button: '{button_clicked}'")
                await asyncio.sleep(3)
            else:
                # Scroll down in increments
                await page.evaluate("window.scrollBy(0, 1500)")
                await asyncio.sleep(2)
                await page.evaluate("window.scrollBy(0, 2500)")
                await asyncio.sleep(2)
                
        # Final extraction
        final_urls = await page.evaluate('''() => {
            const anchors = Array.from(document.querySelectorAll('a[href*="/products/"]'));
            return anchors.map(a => a.href.split('?')[0]).filter(href => href.endsWith('.html'));
        }''')
        for u in final_urls:
            discovered_urls.add(u)
            
    sorted_urls = sorted(list(discovered_urls))
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_urls, f, indent=2)
        
    duration = time.time() - start_time
    print(f"\n========================================================")
    print(f"URL DISCOVERY COMPLETE")
    print(f"Discovered: {len(sorted_urls)} product URLs")
    print(f"Duration:   {duration:.1f} seconds")
    print(f"Saved to:   {OUTPUT_PATH}")
    print(f"========================================================")
    return sorted_urls

if __name__ == "__main__":
    asyncio.run(discover_urls())
