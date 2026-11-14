import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = "C:/Users/Jahangir/.gemini/antigravity/brain/5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"
BASE_URL = "https://therareavenue.com"

def run_visual_audit():
    print("Launching Playwright with Chrome...")
    with sync_playwright() as p:
        # 1. Desktop Visual Verification
        browser = p.chromium.launch(channel="chrome", headless=True)
        desktop_context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = desktop_context.new_page()
        print(f"Navigating to {BASE_URL} on Desktop (1440x900)...")
        page.goto(BASE_URL, wait_until="networkidle", timeout=45000)
        time.sleep(2)

        # Baseline Desktop Header
        desktop_header_path = os.path.join(ARTIFACTS_DIR, "live_desktop_beauty_header.png")
        page.screenshot(path=desktop_header_path, full_page=False)
        print(f"Captured: {desktop_header_path}")

        # Hover / Open Beauty Mega-Menu
        print("Hovering on Beauty nav item...")
        beauty_trigger = page.locator("summary[data-title='Beauty']")
        if beauty_trigger.count() > 0:
            beauty_trigger.first.hover()
            time.sleep(1)
            # Evaluate open if needed
            page.evaluate("""() => {
                const trigger = document.querySelector("summary[data-title='Beauty']");
                if (trigger) {
                    const details = trigger.closest('details');
                    if (details) details.setAttribute('open', 'true');
                }
            }""")
            time.sleep(1)
            beauty_mega_path = os.path.join(ARTIFACTS_DIR, "live_desktop_beauty_mega.png")
            page.screenshot(path=beauty_mega_path, full_page=False)
            print(f"Captured: {beauty_mega_path}")
        else:
            print("WARNING: Beauty trigger not found on desktop!")

        # Hover / Open Brands Mega-Menu to verify Curated Directory A-Z
        print("Opening Brands mega-menu...")
        page.evaluate("""() => {
            document.querySelectorAll('details.luxury-nav__details').forEach(d => d.removeAttribute('open'));
            const trigger = document.querySelector("summary[data-title='Brands']");
            if (trigger) {
                const details = trigger.closest('details');
                if (details) details.setAttribute('open', 'true');
            }
        }""")
        time.sleep(1)
        brands_mega_path = os.path.join(ARTIFACTS_DIR, "live_desktop_brands_beauty_mega.png")
        page.screenshot(path=brands_mega_path, full_page=False)
        print(f"Captured: {brands_mega_path}")

        desktop_context.close()

        # 2. Mobile Visual Verification (iPhone 14 / standard 390x844)
        print("\nOpening Mobile Viewport (390x844)...")
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        mobile_page = mobile_context.new_page()
        mobile_page.goto(BASE_URL, wait_until="networkidle", timeout=45000)
        time.sleep(2)

        # Click hamburger menu / open drawer
        print("Opening mobile navigation drawer...")
        menu_button = mobile_page.locator("button[aria-label*='menu' i], .header__icon--menu, summary.header__icon--menu, .header-drawer__toggle")
        if menu_button.count() > 0:
            menu_button.first.click()
            time.sleep(1.5)
        else:
            # Fallback evaluate open drawer
            mobile_page.evaluate("""() => {
                const drawer = document.querySelector('header-drawer, .header-drawer, details.menu-drawer-container');
                if (drawer) {
                    drawer.setAttribute('open', 'true');
                    const inner = drawer.querySelector('.menu-drawer');
                    if (inner) inner.style.transform = 'none';
                }
            }""")
            time.sleep(1.5)

        mobile_drawer_path = os.path.join(ARTIFACTS_DIR, "live_mobile_drawer_beauty.png")
        mobile_page.screenshot(path=mobile_drawer_path, full_page=False)
        print(f"Captured: {mobile_drawer_path}")

        # Expand Beauty & Cosmetics accordion
        print("Expanding Beauty & Cosmetics accordion in drawer...")
        mobile_page.evaluate("""() => {
            const titles = Array.from(document.querySelectorAll('.luxury-lvl1-title'));
            const beautyTitle = titles.find(t => t.textContent.includes('Beauty'));
            if (beautyTitle) {
                const item = beautyTitle.closest('.luxury-lvl1-item');
                if (item) {
                    item.classList.add('is-open');
                    const body = item.querySelector('.luxury-accordion__body');
                    if (body) body.style.display = 'block';
                }
            }
        }""")
        time.sleep(1)
        mobile_beauty_path = os.path.join(ARTIFACTS_DIR, "live_mobile_beauty_accordion.png")
        mobile_page.screenshot(path=mobile_beauty_path, full_page=False)
        print(f"Captured: {mobile_beauty_path}")

        # Expand Designers & Maisons accordion to show Beauty Maisons
        print("Expanding Designers & Maisons accordion...")
        mobile_page.evaluate("""() => {
            const titles = Array.from(document.querySelectorAll('.luxury-lvl1-title'));
            const brandsTitle = titles.find(t => t.textContent.includes('Designers') || t.textContent.includes('Maisons'));
            if (brandsTitle) {
                const item = brandsTitle.closest('.luxury-lvl1-item');
                if (item) {
                    item.classList.add('is-open');
                    const body = item.querySelector('.luxury-accordion__body');
                    if (body) body.style.display = 'block';
                }
            }
            const subTitles = Array.from(document.querySelectorAll('.luxury-lvl2-title'));
            const beautySub = subTitles.find(t => t.textContent.includes('Beauty'));
            if (beautySub) {
                const subItem = beautySub.closest('.luxury-lvl2-item');
                if (subItem) {
                    subItem.classList.add('is-open');
                    const subBody = subItem.querySelector('.luxury-sub-accordion__body');
                    if (subBody) subBody.style.display = 'block';
                }
            }
        }""")
        time.sleep(1)
        mobile_brands_path = os.path.join(ARTIFACTS_DIR, "live_mobile_beauty_maisons.png")
        mobile_page.screenshot(path=mobile_brands_path, full_page=False)
        print(f"Captured: {mobile_brands_path}")

        browser.close()
        print("\nVisual audit completed successfully!")

if __name__ == "__main__":
    run_visual_audit()
