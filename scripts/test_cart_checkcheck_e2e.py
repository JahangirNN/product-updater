import asyncio
import os
import json
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_e2e():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Step 1: Clear cart
        print("1. Clearing cart...")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1000)

        # Step 2: Navigate directly to Tissot Carson watch
        watch_url = "https://therareavenue.com/products/tissot-carson-watch-t1224071105100"
        print(f"2. Navigating to Watch PDP: {watch_url}")
        await page.goto(watch_url)
        await page.wait_for_load_state("networkidle")

        # Step 3: Check CheckCheck certificate toggle
        print("3. Checking CheckCheck toggle...")
        cc_checkbox = page.locator("#checkcheck-addon-checkbox")
        await cc_checkbox.wait_for(state="attached", timeout=10000)
        # Scroll into view and check
        await cc_checkbox.scroll_into_view_if_needed()
        if not await cc_checkbox.is_checked():
            await cc_checkbox.check()
        print(f"CheckCheck checked state: {await cc_checkbox.is_checked()}")

        # Step 4: Click Add to Cart
        print("4. Clicking Add to Cart on watch PDP...")
        add_btn = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await add_btn.wait_for(state="visible", timeout=10000)
        await add_btn.click()
        
        # Wait for cart drawer or network
        print("Waiting for cart update...")
        await page.wait_for_timeout(4000)

        # Ensure cart drawer is open
        cart_drawer = page.locator("cart-drawer-component, #cart-drawer, .cart-drawer")
        if await cart_drawer.count() > 0:
            print("Cart drawer found.")

        # Capture screenshot 1: Cart drawer with Watch + Certificate
        screenshot_1 = os.path.join(SCREENSHOT_DIR, "cart_drawer_watch_with_cert.png")
        await page.screenshot(path=screenshot_1)
        print(f"Captured screenshot 1: {screenshot_1}")

        # Step 5: Navigate directly to Coach Pouch (no certificate)
        coach_url = "https://therareavenue.com/products/pouch-in-signature-canvas"
        print(f"5. Navigating to Coach PDP: {coach_url}")
        await page.goto(coach_url)
        await page.wait_for_load_state("networkidle")

        # Verify CheckCheck toggle is UNCHECKED on Coach product
        cc_checkbox2 = page.locator("#checkcheck-addon-checkbox")
        if await cc_checkbox2.count() > 0:
            is_checked2 = await cc_checkbox2.is_checked()
            print(f"Coach CheckCheck checked state (should be False): {is_checked2}")

        # Step 6: Click Add to Cart for Coach pouch
        print("6. Clicking Add to Cart on Coach PDP...")
        add_btn2 = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await add_btn2.wait_for(state="visible", timeout=10000)
        await add_btn2.click()
        await page.wait_for_timeout(4000)

        # Capture screenshot 2: Multi-item cart drawer showing pairing
        screenshot_2 = os.path.join(SCREENSHOT_DIR, "cart_drawer_multi_items_pairing.png")
        await page.screenshot(path=screenshot_2)
        print(f"Captured screenshot 2: {screenshot_2}")

        # Step 7: Inspect cart.js API response
        print("7. Fetching /cart.js payload...")
        await page.goto("https://therareavenue.com/cart.js")
        cart_content = await page.inner_text("body")
        try:
            cart_json = json.loads(cart_content)
            items = cart_json.get("items", [])
            print(f"Total Cart Items: {len(items)}")
            for idx, item in enumerate(items):
                print(f"--- Line Item {idx+1} ---")
                print(f"Title: {item.get('title')}")
                print(f"Quantity: {item.get('quantity')}")
                print(f"Price: ₹{item.get('price')/100:.2f}")
                print(f"Properties: {json.dumps(item.get('properties'), indent=2)}")
        except Exception as e:
            print("Cart parsing error:", e)

        # Step 8: Visit cart page (/cart)
        print("8. Navigating to /cart full page...")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("networkidle")
        screenshot_3 = os.path.join(SCREENSHOT_DIR, "cart_page_full_view.png")
        await page.screenshot(path=screenshot_3)
        print(f"Captured screenshot 3: {screenshot_3}")

        await browser.close()
        print("E2E Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_e2e())
