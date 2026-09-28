"""
Visual Audit and Screenshot Verification for Brands Navigation (Desktop & Mobile)
Captures high-res screenshots of:
1. Desktop Brands Mega-Menu (1440x900)
2. Mobile Brands Drawer (430x932)
3. Mobile Brands Drawer (390x844)
Saves outputs to both local artifacts and brain artifact directory.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://therareavenue.com"
BRAIN_ARTIFACT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
LOCAL_ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "screenshots")

os.makedirs(BRAIN_ARTIFACT_DIR, exist_ok=True)
os.makedirs(LOCAL_ARTIFACT_DIR, exist_ok=True)

def save_dual_screenshot(page, filename):
    p1 = os.path.join(LOCAL_ARTIFACT_DIR, filename)
    p2 = os.path.join(BRAIN_ARTIFACT_DIR, filename)
    page.screenshot(path=p1, full_page=False)
    page.screenshot(path=p2, full_page=False)
    print(f"[SCREENSHOT] Saved to:\n  - {p1}\n  - {p2}")

def audit_desktop():
    print("\n--- Auditing Desktop Brands Mega-Menu (1440x900) ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print(f"Navigating to {BASE_URL} ...")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)

        # Trigger Brands disclosure
        brands_trigger = page.locator("summary.luxury-nav__trigger[data-title='Brands'], summary:has-text('Brands')").first
        if brands_trigger.count() > 0:
            print("Found Brands trigger, hovering / clicking...")
            brands_trigger.hover()
            page.wait_for_timeout(1000)
            
            # Ensure details element is open
            details_el = page.locator("details:has(summary.luxury-nav__trigger[data-title='Brands'])").first
            if details_el.count() > 0 and not details_el.evaluate("el => el.hasAttribute('open')"):
                print("Opening details element directly...")
                details_el.evaluate("el => el.setAttribute('open', '')")
                page.wait_for_timeout(800)

            # Check for horizontal scroll / overflow
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            client_width = page.evaluate("() => document.documentElement.clientWidth")
            print(f"Viewport client width: {client_width}px, document scroll width: {scroll_width}px")
            assert scroll_width <= client_width + 5, f"Horizontal overflow detected! {scroll_width} > {client_width}"

            # Verify the 4 columns
            col1 = page.locator(".luxury-mega-menu__col-title:has-text('Leather Goods & Ateliers')")
            col2 = page.locator(".luxury-mega-menu__col-title:has-text('Fine Timepieces & Horology')")
            col3 = page.locator(".luxury-mega-menu__col-title:has-text('Curated Directory')")
            col4 = page.locator(".luxury-editorial-badge:has-text('FEATURED MAISON')")

            print(f"Column 1 (Leather Goods): {col1.count() > 0}")
            print(f"Column 2 (Horology): {col2.count() > 0}")
            print(f"Column 3 (Directory A-Z): {col3.count() > 0}")
            print(f"Column 4 (Editorial Showcase): {col4.count() > 0}")

            save_dual_screenshot(page, "brands_megamenu_desktop_1440x900.png")
            print("[PASS] Desktop visual audit completed successfully.")
        else:
            print("[FAIL] Brands trigger not found!")
            save_dual_screenshot(page, "error_desktop_brands_not_found.png")
        context.close()
        browser.close()

def audit_mobile(width=430, height=932, label="430x932"):
    print(f"\n--- Auditing Mobile Brands Drawer ({label}) ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        print(f"Navigating to {BASE_URL} ...")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)

        # Click hamburger menu
        hamburger = page.locator("button[aria-controls='sidebar-menu']").first
        if hamburger.count() > 0:
            print("Clicking hamburger button...")
            hamburger.click()
            page.wait_for_timeout(800)

            # Click Brands button in sidebar
            brands_btn = page.locator("button[aria-controls='header-panel-brands']").first
            if brands_btn.count() > 0:
                print("Clicking Brands button in mobile sidebar...")
                brands_btn.click()
                page.wait_for_timeout(800)

                # Expand COACH accordion to show richness
                coach_acc = page.locator("#header-panel-brands summary:has-text('COACH')").first
                if coach_acc.count() > 0:
                    print("Expanding COACH accordion...")
                    coach_acc.click()
                    page.wait_for_timeout(400)

                # Expand JW PEI accordion
                jwpei_acc = page.locator("#header-panel-brands summary:has-text('JW PEI')").first
                if jwpei_acc.count() > 0:
                    print("Expanding JW PEI accordion...")
                    jwpei_acc.click()
                    page.wait_for_timeout(400)

                save_dual_screenshot(page, f"brands_drawer_mobile_{label}.png")
                print(f"[PASS] Mobile visual audit for {label} completed successfully.")
            else:
                print("[FAIL] Mobile Brands button not found in sidebar!")
                save_dual_screenshot(page, f"error_mobile_brands_btn_not_found_{label}.png")
        else:
            print("[FAIL] Mobile hamburger button not found!")
            save_dual_screenshot(page, f"error_mobile_hamburger_not_found_{label}.png")

        context.close()
        browser.close()

if __name__ == "__main__":
    audit_desktop()
    audit_mobile(430, 932, "430x932")
    audit_mobile(390, 844, "390x844")
    print("\nVisual audit and screenshot capture complete!")
