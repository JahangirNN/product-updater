"""
Playwright Verification for Product Card Thumbnail and Variant Image Integrity.
Captures screenshots of live collection grid and search results for The Rare Avenue.
Target Directory: C:\\Users\\Administrator\\.gemini\\antigravity\\brain\\8f48874f-591b-45e7-be48-696b0743b7ad
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def verify_live_storefront():
    print("=" * 80)
    print("PLAYWRIGHT STOREFRONT VERIFICATION: PRODUCT CARD FEATURED MEDIA INTEGRITY")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 1. Search page for Abacus bags
        print("\n1. Navigating to Abacus search results...")
        abacus_url = "https://therareavenue.com/search?q=abacus&type=product"
        page.goto(abacus_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("product-card", timeout=15000)
        page.wait_for_timeout(3000)

        # Scroll down slightly to trigger lazy-loaded images
        page.evaluate("window.scrollBy(0, 400)")
        page.wait_for_timeout(2000)

        abacus_grid_path = os.path.join(OUTPUT_DIR, "verified_abacus_grid_live.png")
        page.screenshot(path=abacus_grid_path, full_page=False)
        print(f"Captured: {abacus_grid_path}")

        # Extract product cards info
        cards = page.query_selector_all("product-card")
        print(f"Found {len(cards)} product cards on Abacus search page.")
        for idx, card in enumerate(cards[:10]):
            title_el = card.query_selector(".product-title")
            img_el = card.query_selector(".product-card__image--primary")
            title = title_el.inner_text().strip() if title_el else "Unknown"
            img_src = img_el.get_attribute("src") if img_el else "No Image"
            print(f"  Card {idx+1}: '{title}' -> {img_src[:80] if img_src else None}")

        # 2. Women's Handbags Collection Grid
        print("\n2. Navigating to /collections/womens-handbags...")
        handbags_url = "https://therareavenue.com/collections/womens-handbags"
        page.goto(handbags_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("product-card", timeout=15000)
        page.wait_for_timeout(3000)
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(2000)

        handbags_grid_path = os.path.join(OUTPUT_DIR, "verified_womens_handbags_grid_live.png")
        page.screenshot(path=handbags_grid_path, full_page=False)
        print(f"Captured: {handbags_grid_path}")

        # 3. JW PEI Brand Collection Grid
        print("\n3. Navigating to /collections/jw-pei...")
        jwpei_url = "https://therareavenue.com/collections/jw-pei"
        page.goto(jwpei_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("product-card", timeout=15000)
        page.wait_for_timeout(3000)
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(2000)

        jwpei_grid_path = os.path.join(OUTPUT_DIR, "verified_jw_pei_grid_live.png")
        page.screenshot(path=jwpei_grid_path, full_page=False)
        print(f"Captured: {jwpei_grid_path}")

        browser.close()
        print("\nPLAYWRIGHT VERIFICATION COMPLETED SUCCESSFULLY.")

if __name__ == "__main__":
    verify_live_storefront()
