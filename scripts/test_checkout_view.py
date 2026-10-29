import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def check_checkout():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Step 1: Clear cart
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1000)

        # Step 2: Add Tissot watch with CheckCheck
        await page.goto("https://therareavenue.com/products/tissot-carson-watch-t1224071105100")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)
        cc_box = page.locator("#checkcheck-addon-checkbox")
        await cc_box.scroll_into_view_if_needed()
        if not await cc_box.is_checked():
            await cc_box.check()
        
        add_btn = page.locator("product-form-component button[type='submit']").first
        await add_btn.click()
        await page.wait_for_timeout(3000)

        # Step 3: Add Coach pouch (no checkcheck)
        await page.goto("https://therareavenue.com/products/pouch-in-signature-canvas")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)
        add_btn2 = page.locator("product-form-component button[type='submit']").first
        await add_btn2.click()
        await page.wait_for_timeout(3000)

        # Step 4: Click Checkout
        print("Navigating to checkout...")
        await page.goto("https://therareavenue.com/checkout")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)

        # If email input exists, fill email and submit
        email_input = page.locator("input[type='email'], input#email")
        if await email_input.count() > 0:
            print("Entering guest/test email...")
            await email_input.fill("vip.buyer@therareavenue.com")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(4000)

        # Capture checkout page screenshot
        screenshot_checkout = os.path.join(SCREENSHOT_DIR, "shopify_checkout_pairing_view.png")
        await page.screenshot(path=screenshot_checkout)
        print(f"Captured checkout screenshot: {screenshot_checkout}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_checkout())
