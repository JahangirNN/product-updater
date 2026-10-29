import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_inner_swap():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()

        print("--- Step 1: Clear Cart ---")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1500)

        print("--- Step 2: Open Coach PDP on mobile ---")
        await page.goto("https://therareavenue.com/products/pouch-in-signature-canvas")
        await page.wait_for_timeout(2000)

        print("--- Step 3: Click Add to Cart ---")
        add_btn = page.locator("button[id^='BuyButtons-ProductSubmitButton']").first
        await add_btn.click()
        await page.wait_for_timeout(2500)

        drawer = page.locator("theme-drawer#cart-drawer")
        is_open = await drawer.evaluate("el => el.hasAttribute('open')")
        print(f"Cart drawer open state: {is_open}")

        print("--- Step 4: Click Add Certificate ---")
        cert_btn = page.locator(".ra-add-cert-btn").first
        await cert_btn.click()
        await page.wait_for_timeout(3500)

        # Check attached cert box in DOM
        has_box = await page.evaluate("() => !!document.querySelector('#cart-drawer .ra-attached-cert-box')")
        print(f"Attached cert box in drawer: {has_box}")

        remove_btn = page.locator(".ra-remove-cert-btn").first
        rem_count = await remove_btn.count()
        print(f"Remove button count in drawer: {rem_count}")

        is_open_end = await drawer.evaluate("el => el.hasAttribute('open')")
        print(f"Cart drawer open state after addition: {is_open_end}")

        shot = os.path.join(SCREENSHOT_DIR, "live_mobile_drawer_success.png")
        await page.screenshot(path=shot)
        print(f"Captured: {shot}")

        if rem_count > 0:
            print("--- Step 5: Click Remove on Certificate ---")
            await remove_btn.click()
            await page.wait_for_timeout(3500)
            is_open_rem = await drawer.evaluate("el => el.hasAttribute('open')")
            print(f"Cart drawer open state after removal: {is_open_rem}")
            has_prompt = await page.evaluate("() => !!document.querySelector('#cart-drawer .ra-add-cert-prompt')")
            print(f"Add prompt reverted: {has_prompt}")
            shot_rem = os.path.join(SCREENSHOT_DIR, "live_mobile_drawer_removed_success.png")
            await page.screenshot(path=shot_rem)
            print(f"Captured: {shot_rem}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_inner_swap())
