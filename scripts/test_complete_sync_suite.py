import asyncio
import os
import json
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def run_complete_suite():
    print("=" * 60)
    print("STARTING COMPLETE CHECKCHECK THEME E2E VERIFICATION SUITE")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0"
        )
        page = await context.new_page()

        # Step 1: Clear Cart
        print("\n--- STEP 1: Clear Cart ---")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(2000)

        # Step 2: Add Tissot Carson Watch with CheckCheck
        print("\n--- STEP 2: Add Tissot Carson Watch with CheckCheck (+699) ---")
        await page.goto("https://therareavenue.com/products/tissot-carson-watch-t1224071105100")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)

        cc_box = page.locator("#checkcheck-addon-checkbox")
        await cc_box.scroll_into_view_if_needed()
        if not await cc_box.is_checked():
            await cc_box.check()
        print(f"CheckCheck checkbox checked: {await cc_box.is_checked()}")

        add_btn = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await add_btn.click()
        await page.wait_for_timeout(4000)

        # Step 3: Open /cart and Verify Initial State
        print("\n--- STEP 3: Navigate to /cart and Verify 1:1 Initial State ---")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)

        shot1 = os.path.join(SCREENSHOT_DIR, "step3_initial_cart.png")
        await page.screenshot(path=shot1)
        print(f"Captured initial cart: {shot1}")

        cart_json = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_json["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_json["items"] if it["variant_id"] == 57721101779110), None)
        print(f"Initial Cart: Total Items={len(cart_json['items'])}, Total Price=INR {cart_json['total_price']/100:.2f}")
        print(f"  Parent: '{parent['title']}' qty={parent['quantity']}")
        print(f"  Cert:   '{cert['title']}' qty={cert['quantity']}")
        assert parent["quantity"] == 1, f"Parent quantity should be 1, got {parent['quantity']}"
        assert cert["quantity"] == 1, f"Certificate quantity should be 1, got {cert['quantity']}"

        # Verify Header Cart Bubble = 1 (Physical only)
        bubble_text = await page.locator("cart-icon [ref='cartBubbleCount'], .cart-bubble__text-count").first.text_content()
        print(f"Header Cart Bubble Count: '{bubble_text.strip()}' (Expected '1')")
        assert bubble_text.strip() == "1", f"Expected bubble count '1', got '{bubble_text.strip()}'"

        # Step 4: Test Quantity Increment (1 -> 2)
        print("\n--- STEP 4: Stepper Increment (1 -> 2) ---")
        plus_btn = page.locator("tr[data-attached-cert-key] button[name='plus']").first
        await plus_btn.scroll_into_view_if_needed()
        await plus_btn.click()
        await page.wait_for_timeout(4000)

        cart_json = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_json["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_json["items"] if it["variant_id"] == 57721101779110), None)
        print(f"After Increment (1->2): Total Price=INR {cart_json['total_price']/100:.2f}")
        print(f"  Parent: qty={parent['quantity']}")
        print(f"  Cert:   qty={cert['quantity']}")

        shot2 = os.path.join(SCREENSHOT_DIR, "step4_increment_to_2.png")
        await page.screenshot(path=shot2)
        print(f"Captured increment: {shot2}")

        assert parent["quantity"] == 2, f"Parent quantity should be 2, got {parent['quantity']}"
        assert cert["quantity"] == 2, f"Certificate quantity should be 2, got {cert['quantity']}"

        # Step 5: Test Quantity Decrement (2 -> 1)
        print("\n--- STEP 5: Stepper Decrement (2 -> 1) ---")
        minus_btn = page.locator("tr[data-attached-cert-key] button[name='minus']").first
        await minus_btn.scroll_into_view_if_needed()
        await minus_btn.click()
        await page.wait_for_timeout(4000)

        cart_json = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_json["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_json["items"] if it["variant_id"] == 57721101779110), None)
        print(f"After Decrement (2->1): Total Price=INR {cart_json['total_price']/100:.2f}")
        print(f"  Parent: qty={parent['quantity']}")
        print(f"  Cert:   qty={cert['quantity']}")

        shot3 = os.path.join(SCREENSHOT_DIR, "step5_decrement_to_1.png")
        await page.screenshot(path=shot3)
        print(f"Captured decrement: {shot3}")

        assert parent["quantity"] == 1, f"Parent quantity should be 1, got {parent['quantity']}"
        assert cert["quantity"] == 1, f"Certificate quantity should be 1, got {cert['quantity']}"

        # Step 6: Test Single Certificate Removal via [Remove]
        print("\n--- STEP 6: Detach Certificate Only via [Remove] ---")
        remove_cert_btn = page.locator(".ra-remove-cert-btn").first
        await remove_cert_btn.click()
        await page.wait_for_timeout(4000)

        cart_json = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"After Detach Cert: Items count={len(cart_json['items'])}")
        assert len(cart_json["items"]) == 1, f"Expected 1 item, got {len(cart_json['items'])}"
        assert cart_json["items"][0]["variant_id"] != 57721101779110, "Certificate should be removed"
        print(f"  Remaining Product: '{cart_json['items'][0]['title']}' qty={cart_json['items'][0]['quantity']}")

        # Verify "+ Add CheckCheck Certificate (+₹699)" prompt appears
        add_cert_btn = page.locator(".ra-add-cert-btn")
        print(f"Has '+ Add CheckCheck Certificate' prompt: {await add_cert_btn.count() > 0}")
        assert await add_cert_btn.count() > 0, "Card must revert to display '+ Add CheckCheck Certificate'"

        shot4 = os.path.join(SCREENSHOT_DIR, "step6_cert_detached.png")
        await page.screenshot(path=shot4)
        print(f"Captured detached: {shot4}")

        # Step 7: Test Re-Adding Certificate from Cart
        print("\n--- STEP 7: Re-Add Certificate to Product from Cart ---")
        await add_cert_btn.first.click()
        await page.wait_for_timeout(4000)

        cart_json = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"After Re-Add: Total items={len(cart_json['items'])}")
        assert len(cart_json["items"]) == 2, f"Expected 2 items, got {len(cart_json['items'])}"
        cert_now = next((it for it in cart_json["items"] if it["variant_id"] == 57721101779110), None)
        assert cert_now is not None, "CheckCheck certificate must be present"
        print(f"  Re-added cert qty={cert_now['quantity']}")

        # Step 8: Test Atomic Product + Certificate Removal (Zero Orphans)
        print("\n--- STEP 8: Atomic Removal of Certified Product (Zero Orphans) ---")
        remove_product_btn = page.locator("tr[data-attached-cert-key] button.cart-items__remove").first
        await remove_product_btn.click()
        await page.wait_for_timeout(4000)

        cart_json = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        remaining = cart_json.get("items", [])
        print(f"After Atomic Removal: Total items remaining={len(remaining)}")
        assert len(remaining) == 0, f"Expected 0 items in cart, got {len(remaining)}"
        print("Cart is completely empty! Zero orphaned certificates left.")

        shot5 = os.path.join(SCREENSHOT_DIR, "step8_empty_cart.png")
        await page.screenshot(path=shot5)
        print(f"Captured empty cart: {shot5}")

        # Step 9: Verify 7-Store PDP CheckCheck Availability
        print("\n--- STEP 9: Verify CheckCheck Widget Across Sample PDPs of All 7 Stores ---")
        sample_pdps = [
            ("Coach", "/products/pouch-in-signature-canvas"),
            ("Jomashop", "/products/tissot-carson-watch-t1224071105100"),
            ("Michael Kors", "/products/michael-kors-oversized-billie-chronograph-quartz-white-dial-mens-watch-mk9221"),
            ("JW PEI", "/products/noor-top-handle-bag-brown-canvas"),
            ("Nordstrom", "/products/mach-remastered-sneaker-men"),
            ("JD Sports", "/products/nike-vomero-roam-women-s-tattoo-tattoo-particle-rose-q2181501"),
            ("Foot Locker", "/products/asics-gel-1130-men-s-black-white-red-42609111"),
        ]

        for store, path in sample_pdps:
            url = f"https://therareavenue.com{path}"
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            chk = page.locator("#checkcheck-addon-checkbox")
            present = await chk.count() > 0
            visible = await chk.is_visible() if present else False
            print(f"  [{store}] {path} -> Present: {present}, Visible: {visible}")
            assert present, f"Missing #checkcheck-addon-checkbox on {store} PDP: {url}"

        await browser.close()
        print("\n" + "=" * 60)
        print("ALL CHECKCHECK & STEPPER SYNC ACCEPTANCE CRITERIA VERIFIED LIVE!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_complete_suite())
