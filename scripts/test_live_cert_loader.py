import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_cert_loaders():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("--- STEP 1: Clear Cart via GET /cart/clear.js ---")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1500)

        print("--- STEP 2: Add Coach Pouch without Certificate ---")
        # Coach Pouch variant ID: 57530143768742
        await page.evaluate("""async () => {
            await fetch('/cart/add.js', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify({ items: [{ id: 57530143768742, quantity: 1 }] })
            });
        }""")
        print("Added Coach Pouch to cart.")

        print("--- STEP 3: Navigate to Cart Page ---")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_timeout(2500)

        add_btn = page.locator(".ra-add-cert-btn").first
        await add_btn.scroll_into_view_if_needed()

        print("--- STEP 4: Click '+ Add CheckCheck Certificate' and Capture In-Flight Loader ---")
        # Intercept or click and instantly capture screenshot
        await add_btn.click()
        # Sleep just 80ms to let the DOM update to the loading state
        await page.wait_for_timeout(80)

        add_loader_screenshot = os.path.join(SCREENSHOT_DIR, "cert_add_loader_active.png")
        await page.screenshot(path=add_loader_screenshot)
        print(f"Captured add loader screenshot: {add_loader_screenshot}")

        # Wait for reload/completion
        await page.wait_for_timeout(3500)

        attached_screenshot = os.path.join(SCREENSHOT_DIR, "cert_attached_state.png")
        await page.screenshot(path=attached_screenshot)
        print(f"Captured attached cert screenshot: {attached_screenshot}")

        print("--- STEP 5: Click '[Remove]' on Certificate and Capture In-Flight Loader ---")
        remove_btn = page.locator(".ra-remove-cert-btn").first
        await remove_btn.scroll_into_view_if_needed()
        await remove_btn.click()
        # Sleep 80ms to capture in-flight loader state
        await page.wait_for_timeout(80)

        remove_loader_screenshot = os.path.join(SCREENSHOT_DIR, "cert_remove_loader_active.png")
        await page.screenshot(path=remove_loader_screenshot)
        print(f"Captured remove loader screenshot: {remove_loader_screenshot}")

        # Wait for removal completion
        await page.wait_for_timeout(3500)

        removed_screenshot = os.path.join(SCREENSHOT_DIR, "cert_after_remove_state.png")
        await page.screenshot(path=removed_screenshot)
        print(f"Captured after remove screenshot: {removed_screenshot}")

        print(">>> ALL LOADER VISUAL CHECKS COMPLETED SUCCESSFULLY! <<<")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_cert_loaders())
