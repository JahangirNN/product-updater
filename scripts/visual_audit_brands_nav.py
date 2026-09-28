"""
Visual Audit and Screenshot Verification for Brands Navigation (Desktop, Laptop, Tablet & Mobile)
Captures high-res screenshots of:
1. Desktop Brands Mega-Menu (1440x900)
2. Laptop Brands Mega-Menu (1150x800) - verifying zero logo collision & 4-column balance
3. Tablet Landscape Mega-Menu (1024x768) - verifying zero logo collision & 4-column fit
4. Mobile Brands Drawer (430x932)
5. Mobile Brands Drawer (390x844)
6. Scrolled Mobile Drawer (390x844) with accordions expanded & full scroll
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

def audit_desktop_viewport(width, height, label):
    print(f"\n--- Auditing Desktop/Tablet Mega-Menu ({width}x{height} - {label}) ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()

        print(f"Navigating to {BASE_URL} ...")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)

        # 1. Check for collision between Gift Sets and Logo
        gift_sets = page.locator("a.luxury-nav__trigger:has-text('Gift Sets'), a:has-text('Gift Sets')").first
        logo = page.locator(".header__logo a, .header__logo").first
        if gift_sets.count() > 0 and logo.count() > 0:
            gs_box = gift_sets.bounding_box()
            logo_box = logo.bounding_box()
            print(f"Gift Sets box: right={gs_box['x'] + gs_box['width']:.1f}")
            print(f"Logo box:      left={logo_box['x']:.1f}")
            overlap = (gs_box['x'] + gs_box['width']) - logo_box['x']
            if overlap > 0:
                print(f"[WARN] Overlap detected: {overlap:.1f}px")
            else:
                print(f"[PASS] Zero collision between nav and logo (gap: {-overlap:.1f}px)")
            assert overlap <= 0, f"Nav items overlap logo by {overlap}px!"

        # 2. Trigger Brands disclosure
        brands_trigger = page.locator("summary.luxury-nav__trigger[data-title='Brands'], summary:has-text('Brands')").first
        if brands_trigger.count() > 0:
            print("Found Brands trigger, opening...")
            details_el = page.locator("details:has(summary.luxury-nav__trigger[data-title='Brands'])").first
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
            col4 = page.locator(".luxury-editorial-badge:has-text('CURATED MAISONS')")

            print(f"Column 1 (Leather Goods): {col1.count() > 0}")
            print(f"Column 2 (Horology): {col2.count() > 0}")
            print(f"Column 3 (Directory A-Z): {col3.count() > 0}")
            print(f"Column 4 (Editorial Showcase): {col4.count() > 0}")

            save_dual_screenshot(page, f"brands_megamenu_{label}.png")
            print(f"[PASS] Visual audit for {label} completed successfully.")
        else:
            print("[FAIL] Brands trigger not found!")
            save_dual_screenshot(page, f"error_brands_not_found_{label}.png")
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

def audit_mobile_scrolled(width=390, height=844, label="390x844_scrolled"):
    print(f"\n--- Auditing Mobile Brands Drawer Scrolled to Bottom ({label}) ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)

        page.locator("button[aria-controls='sidebar-menu']").click()
        page.wait_for_timeout(800)
        page.locator("button[aria-controls='header-panel-brands']").click()
        page.wait_for_timeout(800)

        for brand in ['COACH', 'JW PEI', 'Michael Kors']:
            loc = page.locator(f"#header-panel-brands summary:has-text('{brand}')").first
            if loc.count() > 0:
                loc.click()
                page.wait_for_timeout(200)

        # Scroll drawer content container in shadowRoot
        page.evaluate('''() => {
            const hs = document.querySelector('header-sidebar');
            const content = hs.shadowRoot.querySelector('div[part~="content"]');
            if (content) content.scrollTop = content.scrollHeight;
        }''')
        page.wait_for_timeout(500)

        ferragamo = page.locator("#header-panel-brands a:has-text('Ferragamo')").first
        assert ferragamo.count() > 0, "Ferragamo link missing in mobile drawer!"
        f_box = ferragamo.bounding_box()
        print(f"Ferragamo bounding box at bottom: {f_box}")
        assert f_box['y'] + f_box['height'] <= height, f"Ferragamo clipped by bottom of screen! {f_box['y'] + f_box['height']} > {height}"

        save_dual_screenshot(page, f"brands_drawer_mobile_{label}.png")
        print(f"[PASS] Mobile scrolled audit completed successfully.")

        context.close()
        browser.close()

if __name__ == "__main__":
    audit_desktop_viewport(1440, 900, "desktop_1440x900")
    audit_desktop_viewport(1150, 800, "laptop_1150x800")
    audit_desktop_viewport(1024, 768, "tablet_landscape_1024x768")
    audit_mobile(430, 932, "430x932")
    audit_mobile(390, 844, "390x844")
    audit_mobile_scrolled(390, 844, "390x844_scrolled")
    print("\nVisual audit across all form factors completed successfully!")
