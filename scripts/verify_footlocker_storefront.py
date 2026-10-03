import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def verify_footlocker_storefront():
    print("=" * 80)
    print("PLAYWRIGHT STOREFRONT VERIFICATION: FOOT LOCKER FOOTWEAR")
    print("=" * 80)

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        targets = [
            ("adidas", "https://therareavenue.com/collections/all/adidas", "footlocker_adidas_plp.png"),
            ("ASICS", "https://therareavenue.com/collections/all/asics", "footlocker_asics_plp.png"),
            ("Nike", "https://therareavenue.com/collections/all/nike", "footlocker_nike_plp.png"),
            ("Men's Footwear", "https://therareavenue.com/collections/men/footwear", "footlocker_mens_shoes_plp.png"),
            ("Women's Footwear", "https://therareavenue.com/collections/women/footwear", "footlocker_womens_shoes_plp.png"),
            ("All Footwear", "https://therareavenue.com/collections/all/footwear", "footlocker_premium_footwear_plp.png")
        ]

        for name, url, shot_name in targets:
            print(f"\nAuditing PLP: {name} ({url})...")
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(2000)

                cards = page.locator(".product-card")
                count = cards.count()
                print(f"  Product Cards Count: {count}")

                # Check prices
                prices = page.locator(".product-card .price, .product-card__price, .price-item").all_inner_texts()
                clean_prices = [p.strip() for p in prices if p.strip()]
                print(f"  Sample Prices ({min(5, len(clean_prices))}): {clean_prices[:5]}")

                # Check for single-swatch omission rule
                # In product-card, swatches are usually .product-card__swatch or similar
                swatch_containers = page.locator(".product-card__swatches, .color-swatches, .card__swatches")
                sc_count = swatch_containers.count()
                print(f"  Swatch Containers Count: {sc_count}")

                shot_path = os.path.join(OUTPUT_DIR, shot_name)
                page.screenshot(path=shot_path, full_page=False)
                print(f"  Screenshot saved: {shot_name}")

                results[name] = {"count": count, "screenshot": shot_name, "ok": count > 0}
            except Exception as e:
                print(f"  Error on {name}: {e}")
                results[name] = {"error": str(e), "ok": False}

        # Verify a sample Foot Locker PDP
        print("\nAuditing sample PDP...")
        # Navigate to adidas collection and click first product
        try:
            page.goto("https://therareavenue.com/collections/all/adidas", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2000)
            first_card_link = page.locator(".product-card a, .card__inner a").first
            pdp_href = first_card_link.get_attribute("href")
            if pdp_href:
                full_pdp_url = "https://therareavenue.com" + pdp_href if pdp_href.startswith("/") else pdp_href
                print(f"Navigating to sample PDP: {full_pdp_url}")
                page.goto(full_pdp_url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(2000)

                title = page.locator("h1").first.inner_text().strip()
                price = page.locator(".price, .product__price").first.inner_text().strip()
                print(f"  PDP Title: {title}")
                print(f"  PDP Price: {price}")

                # Check option selectors (size buttons/dropdown)
                options = page.locator(".product-form__input, fieldset, select, .variant-picker").all_inner_texts()
                print(f"  Option elements count: {len(options)}")

                pdp_shot = os.path.join(OUTPUT_DIR, "footlocker_sample_pdp.png")
                page.screenshot(path=pdp_shot, full_page=False)
                print(f"  PDP Screenshot saved: footlocker_sample_pdp.png")
                results["Sample PDP"] = {"title": title, "price": price, "url": full_pdp_url, "ok": True}
        except Exception as pe:
            print(f"  PDP audit error: {pe}")
            results["Sample PDP"] = {"error": str(pe), "ok": False}

        browser.close()

    print("\n" + "=" * 80)
    print("PLAYWRIGHT STOREFRONT VERIFICATION SUMMARY:")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("=" * 80)

if __name__ == "__main__":
    verify_footlocker_storefront()
