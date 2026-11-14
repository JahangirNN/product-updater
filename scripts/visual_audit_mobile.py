import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = "C:/Users/Jahangir/.gemini/antigravity/brain/5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"
BASE_URL = "https://therareavenue.com"

def run_mobile_audit():
    print("Launching Playwright for Mobile verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page = mobile_context.new_page()
        print(f"Navigating to {BASE_URL} on Mobile (390x844)...")
        page.goto(BASE_URL, wait_until="networkidle", timeout=45000)
        time.sleep(2)

        # 1. Baseline mobile header (verify hamburger menu icon visible)
        header_path = os.path.join(ARTIFACTS_DIR, "live_mobile_header_icon.png")
        page.screenshot(path=header_path, full_page=False)
        print(f"Captured: {header_path}")

        # 2. Open drawer by clicking hamburger summary or triggering details
        print("Clicking mobile menu trigger...")
        page.evaluate("""() => {
            const summary = document.querySelector('.header__icon--menu');
            if (summary) {
                summary.click();
            } else {
                const details = document.querySelector('#Details-menu-drawer-container');
                if (details) details.setAttribute('open', '');
            }
        }""")
        time.sleep(1.5)

        drawer_path = os.path.join(ARTIFACTS_DIR, "live_mobile_drawer_beauty.png")
        page.screenshot(path=drawer_path, full_page=False)
        print(f"Captured: {drawer_path}")

        # 3. Expand Beauty & Cosmetics accordion
        print("Clicking Beauty & Cosmetics accordion...")
        page.evaluate("""() => {
            const titles = Array.from(document.querySelectorAll('.luxury-lvl1-title'));
            const beautyTitle = titles.find(t => t.textContent.includes('Beauty'));
            if (beautyTitle) {
                const header = beautyTitle.closest('.luxury-lvl1-header');
                if (header) header.click();
            }
        }""")
        time.sleep(1.2)

        beauty_path = os.path.join(ARTIFACTS_DIR, "live_mobile_beauty_accordion.png")
        page.screenshot(path=beauty_path, full_page=False)
        print(f"Captured: {beauty_path}")

        # 4. Expand Designers & Maisons -> Luxury Beauty Maisons
        print("Clicking Designers & Maisons -> Luxury Beauty Maisons...")
        page.evaluate("""() => {
            const titles = Array.from(document.querySelectorAll('.luxury-lvl1-title'));
            const brandsTitle = titles.find(t => t.textContent.includes('Designers'));
            if (brandsTitle) {
                const header = brandsTitle.closest('.luxury-lvl1-header');
                if (header) header.click();
            }
        }""")
        time.sleep(0.8)

        page.evaluate("""() => {
            const subTitles = Array.from(document.querySelectorAll('.luxury-lvl2-title'));
            const beautySub = subTitles.find(t => t.textContent.includes('Beauty'));
            if (beautySub) {
                const subHeader = beautySub.closest('.luxury-lvl2-header');
                if (subHeader) subHeader.click();
            }
        }""")
        time.sleep(1.2)

        maisons_path = os.path.join(ARTIFACTS_DIR, "live_mobile_beauty_maisons.png")
        page.screenshot(path=maisons_path, full_page=False)
        print(f"Captured: {maisons_path}")

        browser.close()
        print("Mobile verification completed!")

if __name__ == "__main__":
    run_mobile_audit()
