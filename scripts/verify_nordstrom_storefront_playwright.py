import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGETS = [
    {
        "name": "on_running",
        "url": "https://therareavenue.com/collections/all?filter.p.vendor=On",
        "expected_vendor": "On"
    },
    {
        "name": "hoka",
        "url": "https://therareavenue.com/collections/all?filter.p.vendor=HOKA",
        "expected_vendor": "HOKA"
    },
    {
        "name": "salomon",
        "url": "https://therareavenue.com/collections/all?filter.p.vendor=Salomon",
        "expected_vendor": "Salomon"
    },
    {
        "name": "men_footwear",
        "url": "https://therareavenue.com/collections/men/footwear",
        "expected_vendor": None
    },
    {
        "name": "women_footwear",
        "url": "https://therareavenue.com/collections/women/footwear",
        "expected_vendor": None
    }
]

def verify_storefront():
    print("=" * 80)
    print("STARTING PLAYWRIGHT STOREFRONT VERIFICATION FOR NORDSTROM PERFORMANCE FOOTWEAR")
    print("=" * 80)

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        for target in TARGETS:
            name = target["name"]
            url = target["url"]
            print(f"\n---> Checking [{name}] at {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)

                # Query product cards
                cards = page.query_selector_all("product-card")
                card_count = len(cards)
                print(f"Product cards rendered: {card_count}")

                # Collect details on up to first 5 cards
                card_samples = []
                for idx, c in enumerate(cards[:5]):
                    title_el = c.query_selector(".product-card__title a, .product-card-title a, a[href*='/products/']")
                    title = title_el.inner_text().strip() if title_el else "Unknown Title"
                    
                    price_el = c.query_selector("price-list, .price-list, .product-card__price")
                    price_text = price_el.inner_text().replace("\n", " ").strip() if price_el else "N/A"

                    # Swatches check
                    swatches = c.query_selector_all(".color-swatch, .swatch, [data-swatch]")
                    swatch_count = len(swatches)

                    card_samples.append({
                        "title": title,
                        "price": price_text,
                        "swatch_count": swatch_count
                    })
                    print(f"  Card {idx+1}: '{title}' | Price: '{price_text}' | Swatches: {swatch_count}")

                # Save screenshot
                screenshot_filename = f"nordstrom_{name}_plp.png"
                screenshot_path = os.path.join(OUTPUT_DIR, screenshot_filename)
                page.screenshot(path=screenshot_path, full_page=False)
                print(f"  Screenshot saved -> {screenshot_path}")

                results[name] = {
                    "url": url,
                    "card_count": card_count,
                    "samples": card_samples,
                    "screenshot": screenshot_path
                }

            except Exception as e:
                print(f"Error checking {name}: {e}")
                results[name] = {"error": str(e)}

        # Specifically check a multi-swatch card and a single-swatch card to verify swatch rule
        print("\n---> Verifying swatch rendering invariants...")
        page.goto("https://therareavenue.com/collections/all?filter.p.vendor=On", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        cards = page.query_selector_all("product-card")
        
        single_swatch_card_found = False
        multi_swatch_card_found = False
        
        for c in cards:
            swatches = c.query_selector_all(".color-swatch, .swatch, [data-swatch]")
            sw_cnt = len(swatches)
            if sw_cnt == 1:
                single_swatch_card_found = True
            elif sw_cnt > 1:
                multi_swatch_card_found = True

        print(f"Single swatch redundant icon present anywhere: {single_swatch_card_found} (Expected: False per PLP theme fix)")
        print(f"Multi-colorway swatches present: {multi_swatch_card_found}")

        browser.close()

    print("=" * 80)
    print("PLAYWRIGHT STOREFRONT VERIFICATION COMPLETE")
    print("=" * 80)
    return results

if __name__ == "__main__":
    verify_storefront()
