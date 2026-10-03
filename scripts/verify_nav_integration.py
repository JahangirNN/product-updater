import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def verify_navigation():
    print("=" * 80)
    print("VERIFYING LIVE STOREFRONT NAVIGATION INTEGRATION")
    print("=" * 80)

    with sync_playwright() as p:
        # 1. Desktop Mega Menus
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("Navigating to home page (desktop)...")
        page.goto("https://therareavenue.com", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        # Hover on BRANDS
        print("Opening BRANDS menu...")
        brands_trigger = page.locator("[data-title='Brands'], .luxury-nav__trigger:has-text('Brands')").first
        brands_trigger.hover()
        page.wait_for_timeout(1500)
        shot_brands = os.path.join(OUTPUT_DIR, "verified_desktop_brands_nav.png")
        page.screenshot(path=shot_brands, full_page=False)
        print("  Saved:", shot_brands)

        # Hover on WOMEN
        print("Opening WOMEN menu...")
        women_trigger = page.locator("[data-title='Women'], .luxury-nav__trigger:has-text('Women')").first
        women_trigger.hover()
        page.wait_for_timeout(1500)
        shot_women = os.path.join(OUTPUT_DIR, "verified_desktop_women_nav.png")
        page.screenshot(path=shot_women, full_page=False)
        print("  Saved:", shot_women)

        # Hover on MEN
        print("Opening MEN menu...")
        men_trigger = page.locator("[data-title='Men'], .luxury-nav__trigger:has-text('Men')").first
        men_trigger.hover()
        page.wait_for_timeout(1500)
        shot_men = os.path.join(OUTPUT_DIR, "verified_desktop_men_nav.png")
        page.screenshot(path=shot_men, full_page=False)
        print("  Saved:", shot_men)

        browser.close()

        # 2. Mobile Drawer Navigation
        mobile_browser = p.chromium.launch(headless=True)
        m_ctx = mobile_browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        m_page = m_ctx.new_page()
        print("\nNavigating to home page (mobile)...")
        m_page.goto("https://therareavenue.com", wait_until="domcontentloaded", timeout=45000)
        m_page.wait_for_timeout(3000)

        # Open mobile drawer menu
        drawer_btn = m_page.locator("button.header__icon--menu, .header__icon--menu, [aria-label*='menu'], summary.header__icon--menu").first
        if drawer_btn.count() > 0:
            drawer_btn.click()
            m_page.wait_for_timeout(1500)

            # Click Brands tab or panel if present
            brands_tab = m_page.locator("button:has-text('Brands'), a:has-text('Brands')").first
            if brands_tab.count() > 0:
                brands_tab.click()
                m_page.wait_for_timeout(1000)

            shot_m_brands = os.path.join(OUTPUT_DIR, "verified_mobile_brands_nav.png")
            m_page.screenshot(path=shot_m_brands, full_page=False)
            print("  Saved mobile brands screenshot:", shot_m_brands)

        mobile_browser.close()

    print("\nNavigation verification completed successfully!")

if __name__ == "__main__":
    verify_navigation()
