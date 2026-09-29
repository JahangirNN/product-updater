import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

TARGET_PRODUCTS = [
    {
        "handle": "celeste-woven-textured-envelope-top-handle-bag-dark-brown",
        "title": "Celeste Woven Textured Envelope Bag",
        "test_swatch": "Black",
        "brand": "JW PEI"
    },
    {
        "handle": "ellie-metal-ring-embellished-top-handle-bag-lemon-yellow",
        "title": "Ellie Metal Ring Embellished Bag",
        "test_swatch": "Denim Blue",
        "brand": "JW PEI"
    },
    {
        "handle": "mini-rowan-crossbody-bag",
        "title": "Mini Rowan Crossbody Bag",
        "test_swatch": "Gold/Pink",
        "brand": "COACH"
    },
    {
        "handle": "nolita-19-in-signature-canvas",
        "title": "Nolita 19 In Signature Canvas",
        "test_swatch": "Gold/Walnut/Black",
        "brand": "COACH"
    }
]

def reproduce_bug():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        for item in TARGET_PRODUCTS:
            handle = item["handle"]
            swatch_to_click = item["test_swatch"]
            url = f"https://therareavenue.com/products/{handle}"
            print(f"\n==========================================")
            print(f"Testing {item['brand']}: {item['title']}")
            print(f"URL: {url}")
            
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)

            # 1. Capture initial screenshot
            init_shot = os.path.join(ARTIFACTS_DIR, f"reproduce_{handle}_initial.png")
            page.screenshot(path=init_shot, full_page=False)

            # Get initial price & main image src
            price_el = page.locator(".price, [data-price], .price-list").first
            init_price = price_el.inner_text().strip().replace("\n", " ") if price_el.count() > 0 else "N/A"
            
            # Main image
            main_img_el = page.locator(".product-gallery__media img").first
            init_img_src = main_img_el.get_attribute("src") if main_img_el.count() > 0 else "N/A"

            # 2. Click swatch
            swatch_selector = f"label:has-text('{swatch_to_click}')"
            swatch = page.locator(swatch_selector).first
            if swatch.count() == 0:
                # Fallback to any non-first label in variant picker
                swatch = page.locator("variant-picker label, .variant-picker label").nth(1)
                swatch_to_click = swatch.inner_text().strip()

            print(f"Clicking swatch: '{swatch_to_click}'...")
            swatch.click()
            page.wait_for_timeout(2500)

            # 3. Capture post-click screenshot
            after_shot = os.path.join(ARTIFACTS_DIR, f"reproduce_{handle}_{swatch_to_click.replace('/', '_').replace(' ', '_')}_selected.png")
            page.screenshot(path=after_shot, full_page=False)

            # Get post-click price & main image src
            after_price = price_el.inner_text().strip().replace("\n", " ") if price_el.count() > 0 else "N/A"
            after_img_src = main_img_el.get_attribute("src") if main_img_el.count() > 0 else "N/A"

            # Also check if gallery scrolled or switched
            active_media = page.evaluate("""() => {
                const g = document.querySelector('product-gallery');
                if (!g) return null;
                const active = g.querySelector('.product-gallery__media:not([aria-hidden="true"]) img') || g.querySelector('.product-gallery__carousel img');
                return {
                    src: active ? active.src : null,
                    carouselIndex: g.carousel ? g.carousel.selectedIndex : null,
                    scrollY: window.scrollY
                };
            }""")

            img_changed = (init_img_src != after_img_src) or (active_media and active_media.get("carouselIndex", 0) > 0) or (active_media and active_media.get("scrollY", 0) > 100)
            
            print(f"Initial Price: {init_price}")
            print(f"After Price:   {after_price}")
            print(f"Initial Image: {init_img_src[:70]}...")
            print(f"After Image:   {after_img_src[:70]}...")
            print(f"Active Media State: {active_media}")
            print(f"BUG CONFIRMED (Image did NOT change): {not img_changed}")

            results.append({
                "product": item["title"],
                "handle": handle,
                "swatch": swatch_to_click,
                "init_price": init_price,
                "after_price": after_price,
                "img_switched": img_changed,
                "initial_screenshot": init_shot,
                "after_screenshot": after_shot
            })

        browser.close()

    print("\n\n==========================================")
    print("REPRODUCTION SUMMARY:")
    for r in results:
        print(f"[{'FAIL (Bug Present)' if not r['img_switched'] else 'PASS'}] {r['product']} ({r['swatch']}) -> Image Switched: {r['img_switched']}")

if __name__ == "__main__":
    reproduce_bug()
