"""
Coach Collection URL Discovery Engine
Crawls all 8 Coach target collections using headless Camoufox browser with automated 'Show More' handling.
Extracts canonical product URLs and groups them cleanly.
Pure functions, zero classes (ADR 0005).
"""
import asyncio
import json
import re
import time
from typing import Dict, List, Set
from camoufox.async_api import AsyncCamoufox

TARGET_COLLECTIONS = [
    {
        "name": "Men Wallets",
        "group": "men_wallets",
        "gender": "Men",
        "url": "https://www.coach.com/shop/outlet/men/wallets",
        "expected": 52
    },
    {
        "name": "Men Shoes",
        "group": "men_shoes",
        "gender": "Men",
        "url": "https://www.coach.com/shop/outlet/men/shoes",
        "expected": 66
    },
    {
        "name": "Men Bags",
        "group": "men_bags",
        "gender": "Men",
        "url": "https://www.coach.com/shop/outlet/men/bags?styleGroup=Backpacks|Briefcases|Crossbody+Bags|Totes+and+Carryalls&index=0",
        "expected": 97
    },
    {
        "name": "Women Nolita Teri",
        "group": "women_bags",
        "gender": "Women",
        "url": "https://www.coach.com/search?q=Nolita+teri",
        "expected": 19
    },
    {
        "name": "Women Bags",
        "group": "women_bags",
        "gender": "Women",
        "url": "https://www.coach.com/shop/outlet/women/bags?pmin=58&pmax=225&page=3",
        "expected": 228
    },
    {
        "name": "Women Wallets",
        "group": "women_wallets",
        "gender": "Women",
        "url": "https://www.coach.com/shop/outlet/women/wallets?pmin=29&pmax=75",
        "expected": 87
    },
    {
        "name": "Women Shoes",
        "group": "women_shoes",
        "gender": "Women",
        "url": "https://www.coach.com/shop/outlet/women/shoes?page=2",
        "expected": 108
    },
    {
        "name": "Women Wristlets",
        "group": "women_wristlets",
        "gender": "Women",
        "url": "https://www.coach.com/shop/outlet/women/wristlets",
        "expected": 36
    }
]


async def crawl_single_collection(browser, col: Dict) -> List[Dict[str, str]]:
    name = col["name"]
    url = col["url"]
    expected = col["expected"]
    group = col["group"]
    gender = col["gender"]

    print(f"\n========================================================")
    print(f"[*] Crawling: {name} (Expected: ~{expected}) -> {url}")
    print(f"========================================================")

    page = await browser.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(4)

        found_links: Set[str] = set()
        stagnant_cycles = 0
        scroll_count = 0
        max_scrolls = max(35, int(expected / 8) + 10)

        while stagnant_cycles < 5 and scroll_count < max_scrolls:
            content = await page.content()
            raw_matches = re.findall(r'href="(/products/[^"?#]+\.html)', content)
            
            new_this_round = 0
            for href in raw_matches:
                full_url = f"https://www.coach.com{href}"
                if full_url not in found_links:
                    found_links.add(full_url)
                    new_this_round += 1

            print(f"  [{name}] Scroll #{scroll_count}: {len(found_links)} unique products (+{new_this_round} new)")

            if len(found_links) >= expected:
                print(f"  [{name}] Target count of {expected} reached!")
                break

            if new_this_round == 0:
                stagnant_cycles += 1
                # Try clicking Show More / Load More button
                try:
                    buttons = await page.query_selector_all("button")
                    for b in buttons:
                        txt = (await b.inner_text()).lower()
                        if any(w in txt for w in ["show more", "load more", "view more"]):
                            if await b.is_visible():
                                print(f"  [{name}] Clicking button: {txt}")
                                await b.click()
                                await asyncio.sleep(2.5)
                                stagnant_cycles = 0
                                break
                except Exception:
                    pass
            else:
                stagnant_cycles = 0

            # Scroll down smoothly
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(2.0)
            scroll_count += 1

        print(f"[✓] {name} complete! Collected {len(found_links)} products.")
        return [{"url": u, "group": group, "gender": gender, "collection": name} for u in sorted(found_links)]

    except Exception as e:
        print(f"[!] Error crawling {name}: {e}")
        return []
    finally:
        await page.close()


async def main():
    start_time = time.time()
    all_results: Dict[str, Dict] = {}

    print("Starting Camoufox browser session for Coach collection crawl...")
    async with AsyncCamoufox(headless=True) as browser:
        # Pre-warm session on coach.com
        prime_page = await browser.new_page()
        try:
            await prime_page.goto("https://www.coach.com/shop/outlet", wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(3)
        finally:
            await prime_page.close()

        for col in TARGET_COLLECTIONS:
            items = await crawl_single_collection(browser, col)
            for it in items:
                u = it["url"]
                if u not in all_results:
                    all_results[u] = it

    elapsed = round(time.time() - start_time, 2)
    print(f"\n========================================================")
    print(f"[✓] Coach Catalog Crawl Complete in {elapsed}s!")
    print(f"[✓] Total Unique Product URLs Discovered: {len(all_results)}")
    print(f"========================================================")

    out_path = "scratch/coach_catalog_urls.json"
    os.makedirs("scratch", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(list(all_results.values()), f, indent=2)
    print(f"Saved catalog URLs to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
