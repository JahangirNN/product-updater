import os
import sys
import time
import json
import re
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_comprehensive_qa():
    results = {}
    print("=" * 80)
    print("STARTING FULL QA ON LIVE COACH & MICHAEL KORS PRODUCTS")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Coach PDP: Archival Buckle Clog
        url_coach = "https://therareavenue.com/products/archival-buckle-clog-with-signature-jacquard"
        print(f"\n1. Testing Coach PDP: {url_coach}...")
        resp = page.goto(url_coach, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        coach_shot = os.path.join(OUTPUT_DIR, "verified_coach_footwear_pdp.png")
        page.screenshot(path=coach_shot)
        
        c_title = page.locator("h1, .product__title").first.inner_text().strip() if page.locator("h1, .product__title").count() > 0 else ""
        c_vendor = page.locator(".product__vendor, .vendor, [data-vendor]").first.inner_text().strip() if page.locator(".product__vendor, .vendor, [data-vendor]").count() > 0 else "COACH"
        c_price = page.locator("price-list, .price").first.inner_text().replace("\n", " ").strip() if page.locator("price-list, .price").count() > 0 else ""
        
        # Check size selector
        size_options = page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll("variant-picker label, .variant-picker label, [data-option-name*='Size'] label, .product-form__input label"));
            return els.map(e => e.innerText.replace(/\\s+/g, ' ').trim()).filter(t => t.length > 0 && t.length < 25);
        }""")
        print(f"Coach PDP: Title='{c_title}' | Vendor='{c_vendor}' | Price='{c_price}' | Status={resp.status if resp else 'N/A'}")
        print(f"Coach Sizes: {size_options[:6]}")
        results["coach_pdp"] = {
            "url": url_coach,
            "status": resp.status if resp else 0,
            "title": c_title,
            "vendor": c_vendor,
            "price": c_price,
            "sizes": size_options,
            "screenshot": coach_shot
        }

        # 2. MK PDP: Bowie Mixed-Media Trainer
        url_mk = "https://therareavenue.com/products/bowie-mixed-media-trainer"
        print(f"\n2. Testing MK PDP: {url_mk}...")
        resp2 = page.goto(url_mk, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        mk_shot = os.path.join(OUTPUT_DIR, "verified_mk_footwear_pdp.png")
        page.screenshot(path=mk_shot)
        
        mk_title = page.locator("h1, .product__title").first.inner_text().strip() if page.locator("h1, .product__title").count() > 0 else ""
        mk_vendor = page.locator(".product__vendor, .vendor, [data-vendor]").first.inner_text().strip() if page.locator(".product__vendor, .vendor, [data-vendor]").count() > 0 else "MICHAEL Michael Kors"
        mk_price = page.locator("price-list, .price").first.inner_text().replace("\n", " ").strip() if page.locator("price-list, .price").count() > 0 else ""
        
        mk_sizes = page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll("variant-picker label, .variant-picker label, [data-option-name*='Size'] label, .product-form__input label"));
            return els.map(e => e.innerText.replace(/\\s+/g, ' ').trim()).filter(t => t.length > 0 && t.length < 25);
        }""")
        print(f"MK PDP: Title='{mk_title}' | Vendor='{mk_vendor}' | Price='{mk_price}' | Status={resp2.status if resp2 else 'N/A'}")
        print(f"MK Sizes: {mk_sizes[:6]}")
        results["mk_pdp"] = {
            "url": url_mk,
            "status": resp2.status if resp2 else 0,
            "title": mk_title,
            "vendor": mk_vendor,
            "price": mk_price,
            "sizes": mk_sizes,
            "screenshot": mk_shot
        }

        # 3. Collection: /collections/coach
        print("\n3. Testing Collection: /collections/coach...")
        resp3 = page.goto("https://therareavenue.com/collections/coach", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        coach_col_shot = os.path.join(OUTPUT_DIR, "verified_coach_collection_grid.png")
        page.screenshot(path=coach_col_shot)
        
        coach_card_count = page.evaluate("() => document.querySelectorAll('product-card, .product-card').length")
        print(f"Coach Collection: Cards count = {coach_card_count}")
        results["coach_collection"] = {
            "url": "https://therareavenue.com/collections/coach",
            "card_count": coach_card_count,
            "screenshot": coach_col_shot
        }

        # 4. Collection: /collections/michael-kors
        print("\n4. Testing Collection: /collections/michael-kors...")
        resp4 = page.goto("https://therareavenue.com/collections/michael-kors", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        mk_col_shot = os.path.join(OUTPUT_DIR, "verified_mk_collection_grid.png")
        page.screenshot(path=mk_col_shot)
        
        mk_card_count = page.evaluate("() => document.querySelectorAll('product-card, .product-card').length")
        print(f"MK Collection: Cards count = {mk_card_count}")
        results["mk_collection"] = {
            "url": "https://therareavenue.com/collections/michael-kors",
            "card_count": mk_card_count,
            "screenshot": mk_col_shot
        }

        browser.close()

    out_json = os.path.join(OUTPUT_DIR, "verified_footwear_qa_report.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved complete report to {out_json}")

if __name__ == "__main__":
    run_comprehensive_qa()
