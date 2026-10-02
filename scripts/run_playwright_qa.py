import asyncio
import os
import sys
from playwright.async_api import async_playwright

BRAIN_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(BRAIN_DIR, exist_ok=True)

STORE_URL = "https://therareavenue.com"

async def run_desktop_tests(browser, width, height, label):
    print(f"\n--- Testing Desktop Viewport {width}x{height} ({label}) ---")
    page = await browser.new_page(viewport={"width": width, "height": height})
    try:
        await page.goto(STORE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # 1. Women mega-menu
        women_summary = page.locator('.luxury-nav__trigger[data-title="Women"]')
        await women_summary.hover()
        await asyncio.sleep(0.5)
        # Check computed styles / overflow
        women_menu = page.locator('details[open] .luxury-mega-menu').first
        is_visible = await women_menu.is_visible()
        scroll_w = await page.evaluate("() => document.documentElement.scrollWidth")
        inner_w = await page.evaluate("() => window.innerWidth")
        print(f"  [{label}] Women Menu Visible: {is_visible}, Page ScrollWidth: {scroll_w}, InnerWidth: {inner_w}")
        assert scroll_w <= inner_w + 1, f"Horizontal scrollbar detected at {width}px: scrollWidth={scroll_w} > innerWidth={inner_w}"
        shot_path = os.path.join(BRAIN_DIR, f"desktop_{label}_women.png")
        await page.screenshot(path=shot_path)
        print(f"  Saved screenshot: {shot_path}")

        # 2. Men mega-menu
        men_summary = page.locator('.luxury-nav__trigger[data-title="Men"]')
        await men_summary.hover()
        await asyncio.sleep(0.5)
        men_menu = page.locator('details[open] .luxury-mega-menu').first
        is_visible = await men_menu.is_visible()
        shot_path = os.path.join(BRAIN_DIR, f"desktop_{label}_men.png")
        await page.screenshot(path=shot_path)
        print(f"  [{label}] Men Menu Visible: {is_visible}, Saved: {shot_path}")

        # 3. Brands mega-menu
        brands_summary = page.locator('.luxury-nav__trigger[data-title="Brands"]')
        await brands_summary.hover()
        await asyncio.sleep(0.5)
        brands_menu = page.locator('details[open] .luxury-mega-menu').first
        is_visible = await brands_menu.is_visible()
        shot_path = os.path.join(BRAIN_DIR, f"desktop_{label}_brands.png")
        await page.screenshot(path=shot_path)
        print(f"  [{label}] Brands Menu Visible: {is_visible}, Saved: {shot_path}")

    finally:
        await page.close()

async def run_mobile_tests(browser):
    print(f"\n--- Testing Mobile Viewport 390x844 (iPhone 12/13/14) ---")
    context = await browser.new_context(
        viewport={"width": 390, "height": 844},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        is_mobile=True,
        has_touch=True
    )
    page = await context.new_page()
    try:
        await page.goto(STORE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Open Hamburger drawer
        hamburger = page.locator('button[aria-controls="sidebar-menu"]')
        await hamburger.click()
        await asyncio.sleep(0.8)

        # 1. Main Drawer
        main_shot = os.path.join(BRAIN_DIR, "mobile_drawer_main.png")
        await page.screenshot(path=main_shot)
        print(f"  Saved main drawer screenshot: {main_shot}")

        # 2. Open Women Sub-Panel
        women_btn = page.locator('#sidebar-menu button[aria-controls="header-panel-women"]')
        await women_btn.click()
        await asyncio.sleep(0.6)

        # Expand Luxury Footwear accordion
        footwear_summary = page.locator('#header-panel-women summary:has-text("Luxury Footwear")')
        await footwear_summary.click()
        await asyncio.sleep(0.5)

        women_shot = os.path.join(BRAIN_DIR, "mobile_drawer_women.png")
        await page.screenshot(path=women_shot)
        print(f"  Saved Women panel (Luxury Footwear open): {women_shot}")

        # Go back
        back_btn = page.locator('#header-panel-women button[data-action="close-panel"]')
        await back_btn.click()
        await asyncio.sleep(0.5)

        # 3. Open Men Sub-Panel
        men_btn = page.locator('#sidebar-menu button[aria-controls="header-panel-men"]')
        await men_btn.click()
        await asyncio.sleep(0.6)

        # Expand Premium Footwear accordion
        men_footwear = page.locator('#header-panel-men summary:has-text("Premium Footwear")')
        await men_footwear.click()
        await asyncio.sleep(0.5)

        men_shot = os.path.join(BRAIN_DIR, "mobile_drawer_men.png")
        await page.screenshot(path=men_shot)
        print(f"  Saved Men panel (Premium Footwear open): {men_shot}")

        # Go back
        back_btn_men = page.locator('#header-panel-men button[data-action="close-panel"]')
        await back_btn_men.click()
        await asyncio.sleep(0.5)

        # 4. Open Brands Sub-Panel
        brands_btn = page.locator('#sidebar-menu button[aria-controls="header-panel-brands"]')
        await brands_btn.click()
        await asyncio.sleep(0.6)

        # Expand COACH accordion to see Footwear pill
        coach_summary = page.locator('#header-panel-brands summary:has-text("COACH")')
        await coach_summary.click()
        await asyncio.sleep(0.5)

        brands_shot = os.path.join(BRAIN_DIR, "mobile_drawer_brands.png")
        await page.screenshot(path=brands_shot)
        print(f"  Saved Brands panel (Coach Footwear): {brands_shot}")

        # Scroll down to Performance & Designer Footwear section (Salomon, On Running, HOKA)
        salomon_link = page.locator('#header-panel-brands a:has-text("Salomon")')
        await salomon_link.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)

        brands_footwear_shot = os.path.join(BRAIN_DIR, "mobile_drawer_brands_footwear.png")
        await page.screenshot(path=brands_footwear_shot)
        print(f"  Saved Brands Footwear drawer: {brands_footwear_shot}")

    finally:
        await context.close()

async def run_url_integrity_tests(browser):
    print(f"\n--- Testing Key Live Navigation URLs in Real Browser ---")
    urls_to_test = [
        "/collections/women?filter.p.tag=Footwear",
        "/collections/men?filter.p.tag=Footwear",
        "/collections/all?filter.p.tag=Footwear",
        "/collections/coach?filter.p.tag=Footwear",
        "/collections/michael-kors?filter.p.tag=Footwear",
        "/collections/all?filter.p.vendor=Salomon",
        "/collections/all?filter.p.vendor=On",
        "/collections/all?filter.p.vendor=HOKA",
        "/collections/instant-ship",
        "/collections/wallets-leather-goods?filter.p.tag=Women",
        "/collections/wallets-leather-goods?filter.p.tag=Men",
        "/collections/designer-eyewear?filter.p.vendor=Michael+Kors",
    ]

    page = await browser.new_page(viewport={"width": 1280, "height": 800})
    passed = 0
    failed = 0
    try:
        for path in urls_to_test:
            full_url = f"{STORE_URL}{path}"
            resp = await page.goto(full_url, wait_until="domcontentloaded", timeout=20000)
            status = resp.status if resp else "NO_RESP"
            content = await page.content()
            has_empty = ("no products found" in content.lower() or "there are no products" in content.lower())
            product_count = await page.locator(".product-card, .product-item").count()

            if status == 200 and not has_empty:
                print(f"  [200 OK] (cards: {product_count}) {path}")
                passed += 1
            else:
                print(f"  [FAIL {status}] Empty: {has_empty} Cards: {product_count} {path}")
                failed += 1
            await asyncio.sleep(0.5)
    finally:
        await page.close()

    print(f"\nURL Integrity Results: {passed} passed, {failed} failed")
    assert failed == 0, f"{failed} URLs failed integrity check!"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            await run_desktop_tests(browser, 1440, 900, "1440")
            await run_desktop_tests(browser, 1280, 800, "1280")
            await run_desktop_tests(browser, 1024, 768, "1024")
            await run_mobile_tests(browser)
            await run_url_integrity_tests(browser)
            print("\nALL PLAYWRIGHT TESTS COMPLETED SUCCESSFULLY!")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
