import asyncio
import os
import sys
import urllib.request
import urllib.error
from playwright.async_api import async_playwright

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts", "navigation_verification")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

STORE_URL = "https://therareavenue.com"

async def run_verification():
    print("=" * 80)
    print("STARTING PLAYWRIGHT NAVIGATION VERIFICATION SUITE")
    print(f"Artifacts output dir: {ARTIFACTS_DIR}")
    print("=" * 80)

    results = {
        "desktop_nav_order": False,
        "gift_sets_absent": False,
        "mega_menus_opened": {},
        "mobile_drawer_items": False,
        "mobile_subpanels_opened": {},
        "url_status_and_products": {},
        "redirects": {},
    }

    async def safe_goto(p, u, wait_until="domcontentloaded", timeout=45000, retries=3):
        for attempt in range(1, retries + 1):
            try:
                return await p.goto(u, wait_until=wait_until, timeout=timeout)
            except Exception as e:
                print(f"[RETRY {attempt}/{retries}] goto {u} failed: {e}")
                if attempt == retries:
                    raise
                await asyncio.sleep(2)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # Part 1: Desktop Navigation & Mega-Menus (1440x900)
        # -------------------------------------------------------------
        print("\n--- 1. DESKTOP HEADER NAVIGATION VERIFICATION ---")
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await safe_goto(page, STORE_URL, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(2)

        # Take full desktop initial screenshot
        desktop_initial_path = os.path.join(ARTIFACTS_DIR, "01_desktop_header_initial.png")
        await page.screenshot(path=desktop_initial_path)
        print(f"Captured: {desktop_initial_path}")

        # Locate all primary triggers
        triggers = page.locator('.header__primary-nav .luxury-nav__trigger')
        trigger_count = await triggers.count()
        print(f"Found {trigger_count} luxury nav triggers in primary nav.")

        trigger_titles = []
        for i in range(trigger_count):
            t = triggers.nth(i)
            title = (await t.get_attribute("data-title")) or (await t.inner_text())
            trigger_titles.append(title.strip().upper())

        print(f"Observed Primary Nav Order: {trigger_titles}")

        expected_order = ["WOMEN", "MEN", "FOOTWEAR", "HANDBAGS", "WATCHES", "ACCESSORIES", "BRANDS"]
        if trigger_titles == expected_order:
            print(f"[PASS] Desktop navigation links match required order: {trigger_titles}")
            results["desktop_nav_order"] = True
        else:
            print(f"[FAIL] Desktop navigation order mismatch! Expected: {expected_order}, Got: {trigger_titles}")

        # Check absence of 'Gift Sets' in header navigation
        has_gift_sets = any("GIFT" in t for t in trigger_titles)
        header_gift_locator = page.locator('.header__primary-nav a:has-text("Gift"), .header__primary-nav summary:has-text("Gift"), header a:has-text("Gift")')
        header_gift_count = await header_gift_locator.count()
        if not has_gift_sets and header_gift_count == 0:
            print("[PASS] 'Gift Sets' is completely absent from desktop header navigation.")
            results["gift_sets_absent"] = True
        else:
            print(f"[FAIL] Found 'Gift Sets' in header navigation (count={header_gift_count})!")

        # Test hovering & opening each of the 4 new category mega-menus
        new_categories = [
            ("Footwear", "02_desktop_megamenu_footwear.png"),
            ("Handbags", "03_desktop_megamenu_handbags.png"),
            ("Watches", "04_desktop_megamenu_watches.png"),
            ("Accessories", "05_desktop_megamenu_accessories.png"),
        ]

        for cat_name, screenshot_file in new_categories:
            print(f"\nTesting Mega-Menu: {cat_name}...")
            cat_trigger = page.locator(f'.luxury-nav__trigger[data-title="{cat_name}"]')
            await cat_trigger.hover()
            await asyncio.sleep(1)

            # Check if details is open or mega-menu is visible
            details_el = page.locator(f'details:has(summary[data-title="{cat_name}"])')
            is_open = await details_el.get_attribute("open") is not None
            
            # If not opened by hover (e.g. click trigger configuration), click to toggle
            if not is_open:
                await cat_trigger.click()
                await asyncio.sleep(1)
                is_open = await details_el.get_attribute("open") is not None

            # Verify mega-menu columns and content
            mega_menu = details_el.locator('.luxury-mega-menu')
            col_titles = await mega_menu.locator('.luxury-mega-menu__col-title').all_inner_texts()
            print(f"  Pillars in {cat_name}: {col_titles}")
            
            promo_heading = await mega_menu.locator('.luxury-mega-menu__promo-heading').inner_text()
            print(f"  Editorial Promo: '{promo_heading}'")

            shot_path = os.path.join(ARTIFACTS_DIR, screenshot_file)
            await page.screenshot(path=shot_path)
            print(f"  Captured: {shot_path}")

            if len(col_titles) >= 4 and len(promo_heading) > 0:
                print(f"  [PASS] Mega-Menu {cat_name} opened and rendered correctly.")
                results["mega_menus_opened"][cat_name] = True
            else:
                print(f"  [FAIL] Mega-Menu {cat_name} missing pillars or promo!")
                results["mega_menus_opened"][cat_name] = False

        await page.close()

        # -------------------------------------------------------------
        # Part 2: Mobile Sidebar Drawer & Sub-panels (390x844 iPhone)
        # -------------------------------------------------------------
        print("\n--- 2. MOBILE DRAWER & DRILL-DOWN PANELS VERIFICATION ---")
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15"
        )
        mob_page = await context.new_page()
        await safe_goto(mob_page, STORE_URL, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(2)

        # Open mobile drawer menu
        menu_btn = mob_page.locator('button[aria-controls="sidebar-menu"]')
        await menu_btn.click()
        await asyncio.sleep(1)

        mobile_drawer_shot = os.path.join(ARTIFACTS_DIR, "06_mobile_drawer_main.png")
        await mob_page.screenshot(path=mobile_drawer_shot)
        print(f"Captured: {mobile_drawer_shot}")

        # Check main panel button list
        drawer_buttons = mob_page.locator('.header-sidebar__main-panel .header-sidebar__linklist-button')
        btn_count = await drawer_buttons.count()
        btn_texts = []
        for i in range(btn_count):
            txt = (await drawer_buttons.nth(i).inner_text()).strip()
            btn_texts.append(txt)
        print(f"Mobile Drawer Main Panel Buttons: {btn_texts}")

        expected_drawer_items = ["Women", "Men", "Footwear", "Handbags", "Watches", "Accessories", "Brands"]
        drawer_has_all = all(item in btn_texts for item in expected_drawer_items)
        drawer_no_gift = not any("gift" in item.lower() for item in btn_texts)

        if drawer_has_all and drawer_no_gift:
            print(f"[PASS] Mobile drawer contains all 7 categories and suppresses Gift Sets.")
            results["mobile_drawer_items"] = True
        else:
            print(f"[FAIL] Mobile drawer buttons incomplete or contains gift sets: {btn_texts}")

        # Test drill-down into each of the 4 new category sub-panels
        mobile_categories = [
            ("Footwear", "header-panel-footwear", "07_mobile_panel_footwear.png"),
            ("Handbags", "header-panel-handbags", "08_mobile_panel_handbags.png"),
            ("Watches", "header-panel-watches", "09_mobile_panel_watches.png"),
            ("Accessories", "header-panel-accessories", "10_mobile_panel_accessories.png"),
        ]

        for cat_name, panel_id, shot_file in mobile_categories:
            print(f"\nOpening Mobile Sub-Panel: {cat_name} ({panel_id})...")
            btn = mob_page.locator(f'button[aria-controls="{panel_id}"]')
            await btn.click()
            await asyncio.sleep(1)

            panel = mob_page.locator(f'#{panel_id}')
            is_visible = await panel.is_visible()

            # Check Shop All button
            shop_all_link = panel.locator('a[style*="font-weight: 600"]').first
            shop_all_text = await shop_all_link.inner_text()
            shop_all_href = await shop_all_link.get_attribute("href")
            print(f"  Sub-panel Shop All: '{shop_all_text}' -> '{shop_all_href}'")

            # Check accordion categories
            accordions = await panel.locator('summary').all_inner_texts()
            print(f"  Sub-categories: {[a.strip() for a in accordions]}")

            panel_shot = os.path.join(ARTIFACTS_DIR, shot_file)
            await mob_page.screenshot(path=panel_shot)
            print(f"  Captured: {panel_shot}")

            # Click back button to return to main panel
            back_btn = panel.locator('button[data-action="close-panel"]')
            await back_btn.click()
            await asyncio.sleep(1)

            if is_visible and len(shop_all_href) > 0 and len(accordions) >= 3:
                print(f"  [PASS] Mobile sub-panel {cat_name} functioned cleanly.")
                results["mobile_subpanels_opened"][cat_name] = True
            else:
                print(f"  [FAIL] Mobile sub-panel {cat_name} did not open or missing content!")
                results["mobile_subpanels_opened"][cat_name] = False

        # -------------------------------------------------------------
        # Part 3: Defensive Route Redirection Test
        # -------------------------------------------------------------
        print("\n--- 3. DEFENSIVE ROUTE REDIRECTION VERIFICATION ---")
        redirect_tests = [
            (f"{STORE_URL}/collections/watches", "/collections/luxury-watches"),
            (f"{STORE_URL}/collections/accessories", "/collections/wallets-accessories"),
        ]

        for req_url, expected_dest in redirect_tests:
            print(f"Testing redirect: {req_url} -> {expected_dest}")
            try:
                await mob_page.goto(req_url, wait_until="commit", timeout=25000)
            except Exception:
                pass
            try:
                await mob_page.wait_for_url(f"**{expected_dest}**", timeout=15000)
            except Exception:
                pass
            await asyncio.sleep(2)
            final_url = mob_page.url
            print(f"  Resolved final URL: {final_url}")
            if expected_dest in final_url:
                print(f"  [PASS] Successfully redirected to {expected_dest}")
                results["redirects"][req_url] = True
            else:
                print(f"  [FAIL] Did not redirect to expected destination! Final: {final_url}")
                results["redirects"][req_url] = False

        await mob_page.close()
        await context.close()

        # -------------------------------------------------------------
        # Part 4: HTTP 200 & Product Population Verification
        # -------------------------------------------------------------
        print("\n--- 4. HTTP 200 & PRODUCT POPULATION VERIFICATION ---")
        primary_collections = [
            ("/collections/premium-footwear", "Premium Footwear"),
            ("/collections/designer-bags", "Designer Bags"),
            ("/collections/luxury-watches", "Luxury Watches"),
            ("/collections/wallets-accessories", "Wallets & Accessories"),
        ]

        check_page = await browser.new_page(viewport={"width": 1440, "height": 900})
        for path, title in primary_collections:
            url = STORE_URL + path
            try:
                resp = await safe_goto(check_page, url, wait_until="domcontentloaded", timeout=40000)
                status = resp.status if resp else 0
                html = await check_page.content()
                has_products = "product-card" in html or "product-item" in html or "product-list" in html or "h-stack" in html
                has_title = title.lower() in html.lower()
                print(f"[{status}] {path} - Products Found: {has_products}, Title Found: {has_title}")
                results["url_status_and_products"][path] = (status == 200 and has_products)
            except Exception as e:
                print(f"[FAIL] {path}: {e}")
                results["url_status_and_products"][path] = False
            await asyncio.sleep(1)

        await check_page.close()
        await browser.close()

    # -------------------------------------------------------------
    # Summary Report
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("VERIFICATION SUITE SUMMARY")
    print("=" * 80)
    for k, v in results.items():
        print(f"{k}: {v}")
    print("=" * 80)

    # Verify all passed
    all_passed = (
        results["desktop_nav_order"] and
        results["gift_sets_absent"] and
        all(results["mega_menus_opened"].values()) and
        results["mobile_drawer_items"] and
        all(results["mobile_subpanels_opened"].values()) and
        all(results["url_status_and_products"].values()) and
        all(results["redirects"].values())
    )

    if all_passed:
        print("\nALL VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
        return True
    else:
        print("\nSOME VERIFICATION CHECKS FAILED!")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_verification())
    if not success:
        sys.exit(1)
