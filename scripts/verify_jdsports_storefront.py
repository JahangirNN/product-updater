import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"

def verify_jdsports_storefront():
    print("Launching Playwright for JD Sports Storefront Multi-Viewport Verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Nike Brand PLP
        print("Auditing Nike Brand PLP...")
        page.goto("https://therareavenue.com/collections/nike", wait_until="networkidle", timeout=60000)
        time.sleep(2)
        nike_path = os.path.join(ARTIFACT_DIR, "jdsports_nike_plp.png")
        page.screenshot(path=nike_path, full_page=False)
        print(f"Captured Nike PLP screenshot: {nike_path}")

        # 2. Men's Footwear PLP - check for ZERO Kids items
        print("Auditing Men's Footwear PLP for zero Kids contamination...")
        page.goto("https://therareavenue.com/collections/mens-shoes", wait_until="networkidle", timeout=60000)
        time.sleep(2)
        mens_path = os.path.join(ARTIFACT_DIR, "jdsports_mens_footwear_plp.png")
        page.screenshot(path=mens_path, full_page=False)
        print(f"Captured Men's Footwear PLP screenshot: {mens_path}")

        # Extract product titles on Men's Shoes page
        titles = page.locator(".product-card__title, .card__heading, h3 a, .product-item__title").all_text_contents()
        kids_leaks = [t for t in titles if any(k in t.lower() for k in ["toddler", "little kids", "big kids", "infant", "crib", "boys", "girls"])]
        print(f"Men's Footwear total visible titles: {len(titles)}")
        print(f"Kids shoes leaking in Men's Footwear: {len(kids_leaks)}")
        if kids_leaks:
            print("  LEAKS DETECTED:", kids_leaks)
        else:
            print("  --> ZERO Kids shoes in Men's Footwear! Invariant verified.")

        # 3. Women's Footwear PLP - check for ZERO Kids items
        print("Auditing Women's Footwear PLP for zero Kids contamination...")
        page.goto("https://therareavenue.com/collections/womens-shoes", wait_until="networkidle", timeout=60000)
        time.sleep(2)
        womens_path = os.path.join(ARTIFACT_DIR, "jdsports_womens_footwear_plp.png")
        page.screenshot(path=womens_path, full_page=False)
        print(f"Captured Women's Footwear PLP screenshot: {womens_path}")

        titles_w = page.locator(".product-card__title, .card__heading, h3 a, .product-item__title").all_text_contents()
        kids_leaks_w = [t for t in titles_w if any(k in t.lower() for k in ["toddler", "little kids", "big kids", "infant", "crib", "boys", "girls"])]
        print(f"Women's Footwear total visible titles: {len(titles_w)}")
        print(f"Kids shoes leaking in Women's Footwear: {len(kids_leaks_w)}")
        if kids_leaks_w:
            print("  LEAKS DETECTED:", kids_leaks_w)
        else:
            print("  --> ZERO Kids shoes in Women's Footwear! Invariant verified.")

        # 4. Premium Footwear PLP
        print("Auditing Premium Footwear Master PLP...")
        page.goto("https://therareavenue.com/collections/premium-footwear", wait_until="networkidle", timeout=60000)
        time.sleep(2)
        pf_path = os.path.join(ARTIFACT_DIR, "jdsports_premium_footwear_plp.png")
        page.screenshot(path=pf_path, full_page=False)
        print(f"Captured Premium Footwear PLP screenshot: {pf_path}")

        # 5. Sample Nike PDP
        print("Auditing Sample Nike Footwear PDP...")
        pdp_url = "https://therareavenue.com/products/womens-nike-dunk-low-patent-leather-casual-shoes-pink-foam-black-white-3337873"
        print(f"Visiting PDP: {pdp_url}")
        page.goto(pdp_url, wait_until="networkidle", timeout=60000)
        time.sleep(2)
        pdp_path = os.path.join(ARTIFACT_DIR, "jdsports_sample_nike_pdp.png")
        page.screenshot(path=pdp_path, full_page=False)
        print(f"Captured Nike PDP screenshot: {pdp_path}")

        browser.close()
        print("Playwright Storefront Audit Complete!")

if __name__ == "__main__":
    verify_jdsports_storefront()
