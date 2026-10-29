import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_live_mobile_drawer():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))

        print("--- Step 1: Clear Cart ---")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1000)

        print("--- Step 2: Open Coach PDP on mobile ---")
        await page.goto("https://therareavenue.com/products/pouch-in-signature-canvas")
        await page.wait_for_timeout(2500)

        print("--- Step 3: Click Add to Cart ---")
        add_btn = page.locator("button[id^='BuyButtons-ProductSubmitButton']").first
        await add_btn.scroll_into_view_if_needed()
        await add_btn.click()

        print("Waiting for drawer to open...")
        await page.wait_for_timeout(2500)

        drawer = page.locator("theme-drawer#cart-drawer")
        is_open = await drawer.evaluate("el => el.hasAttribute('open')")
        print(f"Cart drawer open state: {is_open}")
        assert is_open, "Drawer did not open after Add to Cart!"

        shot1 = os.path.join(SCREENSHOT_DIR, "mobile_drawer_open_clean.png")
        await page.screenshot(path=shot1)
        print(f"Captured: {shot1}")

        print("--- Step 4: Click '+ Add CheckCheck Certificate' inside drawer ---")
        cert_btn = page.locator(".ra-add-cert-btn").first
        await cert_btn.click()

        # Check in-flight state (250ms)
        await page.wait_for_timeout(250)
        is_open_inflight = await drawer.evaluate("el => el.hasAttribute('open')")
        print(f"Cart drawer in-flight open state: {is_open_inflight}")
        assert is_open_inflight, "BUG: Drawer closed during in-flight addition!"

        shot2 = os.path.join(SCREENSHOT_DIR, "mobile_drawer_cert_inflight_clean.png")
        await page.screenshot(path=shot2)
        print(f"Captured: {shot2}")

        # Wait for addition to complete
        await page.wait_for_timeout(3500)
        is_open_attached = await drawer.evaluate("el => el.hasAttribute('open')")
        print(f"Cart drawer open state after addition: {is_open_attached}")
        assert is_open_attached, "BUG: Drawer closed after addition completed!"

        shot3 = os.path.join(SCREENSHOT_DIR, "mobile_drawer_cert_attached_clean.png")
        await page.screenshot(path=shot3)
        print(f"Captured: {shot3}")

        print("--- Step 5: Click 'Remove' on Certificate inside drawer ---")
        remove_btn = page.locator(".ra-remove-cert-btn").first
        rem_count = await remove_btn.count()
        print(f"Remove button count in drawer: {rem_count}")
        assert rem_count > 0, "No remove button found in attached certificate box!"

        await remove_btn.click()

        # Check remove in-flight state (250ms)
        await page.wait_for_timeout(250)
        is_open_rem_inflight = await drawer.evaluate("el => el.hasAttribute('open')")
        print(f"Cart drawer in-flight removal open state: {is_open_rem_inflight}")
        assert is_open_rem_inflight, "BUG: Drawer closed during in-flight removal!"

        shot4 = os.path.join(SCREENSHOT_DIR, "mobile_drawer_remove_inflight_clean.png")
        await page.screenshot(path=shot4)
        print(f"Captured: {shot4}")

        # Wait for removal to complete
        await page.wait_for_timeout(3500)
        is_open_reverted = await drawer.evaluate("el => el.hasAttribute('open')")
        print(f"Cart drawer open state after removal: {is_open_reverted}")
        assert is_open_reverted, "BUG: Drawer closed after removal completed!"

        shot5 = os.path.join(SCREENSHOT_DIR, "mobile_drawer_cert_removed_clean.png")
        await page.screenshot(path=shot5)
        print(f"Captured: {shot5}")

        print(">>> ALL MOBILE DRAWER CHECKS PASSED WITH FLYING COLORS! <<<")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_live_mobile_drawer())
