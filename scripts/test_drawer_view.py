import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_drawer_view():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Step 1: Clear Cart
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1000)

        # Step 2: Add Tissot Watch with CheckCheck
        await page.goto("https://therareavenue.com/products/tissot-carson-watch-t1224071105100")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        cc_box = page.locator("#checkcheck-addon-checkbox")
        await cc_box.scroll_into_view_if_needed()
        if not await cc_box.is_checked():
            await cc_box.check()

        add_btn = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await add_btn.click()
        await page.wait_for_timeout(3500)

        # Step 3: Add Coach Pouch without CheckCheck
        await page.goto("https://therareavenue.com/products/pouch-in-signature-canvas")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        add_btn2 = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await add_btn2.click()
        await page.wait_for_timeout(3500)

        # Capture Cart Drawer view
        shot_drawer = os.path.join(SCREENSHOT_DIR, "attached_cert_drawer_view.png")
        await page.screenshot(path=shot_drawer)
        print(f"Captured: {shot_drawer}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_drawer_view())
