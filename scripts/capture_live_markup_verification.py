import os
import sys
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

def capture_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        targets = [
            ("https://therareavenue.com/collections/beauty", "live_markup_plp_beauty.png"),
            ("https://therareavenue.com/collections/rhode", "live_markup_plp_rhode.png"),
            ("https://therareavenue.com/collections/summer-fridays", "live_markup_plp_summer_fridays.png"),
            ("https://therareavenue.com/collections/refy", "live_markup_plp_refy.png"),
            ("https://therareavenue.com/products/refy-mini-brow-sculpt-shaping-and-lifting-gel-with-strong-hold-p522175", "live_markup_pdp_refy_mini_brow.png"),
            ("https://therareavenue.com/products/saie-dew-blush-liquid-cream-blush-p469825", "live_markup_pdp_saie_dew_blush.png"),
        ]

        for url, filename in targets:
            try:
                print(f"Navigating to {url}...")
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(3500)
                save_path = os.path.join(ARTIFACT_DIR, filename)
                page.screenshot(path=save_path)
                print(f"Captured: {filename}")
            except Exception as e:
                print(f"Failed to capture {url}: {e}")

        browser.close()
        print("Done.")

if __name__ == "__main__":
    capture_screenshots()
