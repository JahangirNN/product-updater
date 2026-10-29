import asyncio
import os
import json
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_all_scenarios():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("--- STEP 1: Clear Cart ---")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1000)

        print("--- STEP 2: Add Tissot Watch with CheckCheck ---")
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

        print("--- STEP 3: Add Coach Pouch without CheckCheck ---")
        await page.goto("https://therareavenue.com/products/pouch-in-signature-canvas")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        add_btn2 = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await add_btn2.click()
        await page.wait_for_timeout(3500)

        # Open cart page to inspect rendering
        print("--- STEP 4: Inspect Cart Page / Drawer with Attached UI ---")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        shot1 = os.path.join(SCREENSHOT_DIR, "attached_cert_multi_products.png")
        await page.screenshot(path=shot1)
        print(f"Captured: {shot1}")

        # Check cart lines count
        rows = await page.locator(".cart-items__table-row").all()
        print(f"Total visible product rows rendered: {len(rows)}")

        # Check if Coach has the + Add prompt
        coach_add_prompt = page.locator(".ra-add-cert-btn")
        print(f"Has '+ Add CheckCheck Certificate' prompt on uncertified item: {await coach_add_prompt.count() > 0}")

        # Check if Tissot has attached cert box
        tissot_cert_box = page.locator(".ra-attached-cert-box")
        print(f"Has attached cert box on certified item: {await tissot_cert_box.count() > 0}")

        print("--- STEP 5: Test Edge Case - Remove Tissot Watch (Must Remove Attached Cert as well) ---")
        # Find remove button for Tissot watch
        # Tissot row is the one containing data-attached-cert-key
        tissot_remove_btn = page.locator("tr[data-attached-cert-key] button.cart-items__remove").first
        if await tissot_remove_btn.count() > 0:
            print("Clicking atomic remove on Tissot watch...")
            await tissot_remove_btn.click()
            await page.wait_for_timeout(3000)
            await page.wait_for_load_state("domcontentloaded")

            shot2 = os.path.join(SCREENSHOT_DIR, "after_removing_certified_product.png")
            await page.screenshot(path=shot2)
            print(f"Captured: {shot2}")

            # Verify cart JSON
            await page.goto("https://therareavenue.com/cart.js")
            cart_data = json.loads(await page.inner_text("body"))
            print("Cart items after removing watch:", len(cart_data.get("items", [])))
            for it in cart_data.get("items", []):
                print(f" - {it['title']} (variant {it['variant_id']})")

        print("--- STEP 6: Test 1-Click Add Certificate to Coach Pouch from Cart ---")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        coach_btn = page.locator(".ra-add-cert-btn").first
        if await coach_btn.count() > 0:
            print("Clicking '+ Add CheckCheck Certificate' on Coach Pouch...")
            await coach_btn.click()
            await page.wait_for_timeout(3000)
            await page.wait_for_load_state("domcontentloaded")

            shot3 = os.path.join(SCREENSHOT_DIR, "after_adding_cert_to_coach.png")
            await page.screenshot(path=shot3)
            print(f"Captured: {shot3}")

            # Check if attached cert box is now visible
            cert_box_now = page.locator(".ra-attached-cert-box")
            print(f"Has attached cert box on Coach Pouch now: {await cert_box_now.count() > 0}")

            # Test Remove Attached Cert
            print("--- STEP 7: Test Removing Certificate Only (Keep Coach Pouch) ---")
            remove_cert_btn = page.locator(".ra-remove-cert-btn").first
            if await remove_cert_btn.count() > 0:
                print("Clicking 'Remove' on attached cert...")
                await remove_cert_btn.click()
                await page.wait_for_timeout(3000)
                await page.wait_for_load_state("domcontentloaded")

                shot4 = os.path.join(SCREENSHOT_DIR, "after_removing_cert_only.png")
                await page.screenshot(path=shot4)
                print(f"Captured: {shot4}")

        await browser.close()
        print("ALL TESTS COMPLETED!")

if __name__ == "__main__":
    asyncio.run(test_all_scenarios())
