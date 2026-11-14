import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = "C:/Users/Jahangir/.gemini/antigravity/brain/5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"
BASE_URL = "https://therareavenue.com"

def run_pdp_audit():
    print("Launching Playwright to verify PDP and Beauty Collection...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 1. Beauty Master Collection PLP
        print("Navigating to /collections/beauty...")
        page.goto(f"{BASE_URL}/collections/beauty", wait_until="networkidle", timeout=45000)
        time.sleep(2)
        plp_path = os.path.join(ARTIFACTS_DIR, "live_plp_beauty_collection.png")
        page.screenshot(path=plp_path, full_page=False)
        print(f"Captured: {plp_path}")

        # 2. Saie Dew Blush PDP (Multi-shade + Multi-size + Varying Price)
        print("Navigating to Saie Dew Blush PDP...")
        page.goto(f"{BASE_URL}/products/saie-dew-blush-liquid-cream-blush-p469825", wait_until="networkidle", timeout=45000)
        time.sleep(2)
        saie_path = os.path.join(ARTIFACTS_DIR, "live_pdp_saie_blush.png")
        page.screenshot(path=saie_path, full_page=False)
        print(f"Captured: {saie_path}")

        # Test swatch selection and size selection
        print("Testing interactive swatch click...")
        swatch = page.locator(".swatch-button, .color-swatch, button[data-option-value], .variant-picker__swatch").first
        if swatch.count() > 0:
            swatch.click()
            time.sleep(1)

        # 3. Gisou Hair Mask PDP (Multi-size volume pricing)
        print("Navigating to Gisou Hair Mask PDP...")
        page.goto(f"{BASE_URL}/products/gisou-honey-gloss-ceramide-therapy-hydrating-hair-mask-p515172", wait_until="networkidle", timeout=45000)
        time.sleep(2)
        gisou_path = os.path.join(ARTIFACTS_DIR, "live_pdp_gisou_mask.png")
        page.screenshot(path=gisou_path, full_page=False)
        print(f"Captured: {gisou_path}")

        browser.close()
        print("PDP visual verification finished successfully!")

if __name__ == "__main__":
    run_pdp_audit()
