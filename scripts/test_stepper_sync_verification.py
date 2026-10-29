import asyncio
import json
import os
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_stepper_synchronization():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("\n=== STEP 1: Clear Cart & Add Tissot Watch with CheckCheck ===")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1000)

        await page.goto("https://therareavenue.com/products/tissot-carson-watch-t1224071105100")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        cc_box = page.locator("#checkcheck-addon-checkbox")
        await cc_box.scroll_into_view_if_needed()
        if not await cc_box.is_checked():
            await cc_box.check()
        print(f"CheckCheck checkbox checked: {await cc_box.is_checked()}")

        add_btn = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await add_btn.click()
        await page.wait_for_timeout(4000)

        print("\n=== STEP 2: Navigate to /cart and Verify Initial State (Qty 1:1) ===")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        # Check cart.js state
        cart_state = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_state["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_state["items"] if it["variant_id"] == 57721101779110), None)
        print(f"Initial: Parent qty={parent['quantity']}, Cert qty={cert['quantity']}, Total price=INR {cart_state['total_price']/100:.2f}")
        assert parent["quantity"] == 1, f"Expected parent qty 1, got {parent['quantity']}"
        assert cert["quantity"] == 1, f"Expected cert qty 1, got {cert['quantity']}"

        shot_initial = os.path.join(SCREENSHOT_DIR, "sync_01_qty_1.png")
        await page.screenshot(path=shot_initial)
        print(f"Captured: {shot_initial}")

        print("\n=== STEP 3: Click '+' Stepper (1 -> 2) ===")
        plus_btn = page.locator("button[name='plus'], cart-quantity-selector-component button[name='plus']").first
        await plus_btn.click()
        await page.wait_for_timeout(4000)

        cart_state = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_state["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_state["items"] if it["variant_id"] == 57721101779110), None)
        print(f"After + (1->2): Parent qty={parent['quantity']}, Cert qty={cert['quantity']}, Total price=INR {cart_state['total_price']/100:.2f}")
        assert parent["quantity"] == 2, f"Expected parent qty 2, got {parent['quantity']}"
        assert cert["quantity"] == 2, f"Expected cert qty 2, got {cert['quantity']}"

        shot_plus1 = os.path.join(SCREENSHOT_DIR, "sync_02_qty_2.png")
        await page.screenshot(path=shot_plus1)
        print(f"Captured: {shot_plus1}")

        print("\n=== STEP 4: Click '+' Stepper (2 -> 3) ===")
        await plus_btn.click()
        await page.wait_for_timeout(4000)

        cart_state = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_state["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_state["items"] if it["variant_id"] == 57721101779110), None)
        print(f"After + (2->3): Parent qty={parent['quantity']}, Cert qty={cert['quantity']}, Total price=INR {cart_state['total_price']/100:.2f}")
        assert parent["quantity"] == 3, f"Expected parent qty 3, got {parent['quantity']}"
        assert cert["quantity"] == 3, f"Expected cert qty 3, got {cert['quantity']}"

        shot_plus2 = os.path.join(SCREENSHOT_DIR, "sync_03_qty_3.png")
        await page.screenshot(path=shot_plus2)
        print(f"Captured: {shot_plus2}")

        print("\n=== STEP 5: Click '-' Stepper (3 -> 2) ===")
        minus_btn = page.locator("button[name='minus'], cart-quantity-selector-component button[name='minus']").first
        await minus_btn.click()
        await page.wait_for_timeout(4000)

        cart_state = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_state["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_state["items"] if it["variant_id"] == 57721101779110), None)
        print(f"After - (3->2): Parent qty={parent['quantity']}, Cert qty={cert['quantity']}, Total price=INR {cart_state['total_price']/100:.2f}")
        assert parent["quantity"] == 2, f"Expected parent qty 2, got {parent['quantity']}"
        assert cert["quantity"] == 2, f"Expected cert qty 2, got {cert['quantity']}"

        shot_minus1 = os.path.join(SCREENSHOT_DIR, "sync_04_qty_2.png")
        await page.screenshot(path=shot_minus1)
        print(f"Captured: {shot_minus1}")

        print("\n=== STEP 6: Click '-' Stepper (2 -> 1) ===")
        await minus_btn.click()
        await page.wait_for_timeout(4000)

        cart_state = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_state["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_state["items"] if it["variant_id"] == 57721101779110), None)
        print(f"After - (2->1): Parent qty={parent['quantity']}, Cert qty={cert['quantity']}, Total price=INR {cart_state['total_price']/100:.2f}")
        assert parent["quantity"] == 1, f"Expected parent qty 1, got {parent['quantity']}"
        assert cert["quantity"] == 1, f"Expected cert qty 1, got {cert['quantity']}"

        shot_minus2 = os.path.join(SCREENSHOT_DIR, "sync_05_qty_1.png")
        await page.screenshot(path=shot_minus2)
        print(f"Captured: {shot_minus2}")

        print("\n=== STEP 7: Detach Certificate Only via [Remove] Button ===")
        remove_cert_btn = page.locator(".ra-remove-cert-btn").first
        await remove_cert_btn.click()
        await page.wait_for_timeout(4000)

        cart_state = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"After Detach Cert: Total items in cart={len(cart_state['items'])}")
        for it in cart_state["items"]:
            print(f" - {it['title']} (variant {it['variant_id']}), qty={it['quantity']}")
        assert len(cart_state["items"]) == 1, f"Expected exactly 1 item remaining, got {len(cart_state['items'])}"
        assert cart_state["items"][0]["variant_id"] != 57721101779110, "Certificate should be removed"

        # Check prompt reverted to + Add CheckCheck Certificate
        add_cert_prompt = page.locator(".ra-add-cert-btn")
        print(f"Prompt reverted to '+ Add CheckCheck Certificate': {await add_cert_prompt.count() > 0}")
        assert await add_cert_prompt.count() > 0, "Card should revert to display '+ Add CheckCheck Certificate'"

        shot_detach = os.path.join(SCREENSHOT_DIR, "sync_06_cert_detached.png")
        await page.screenshot(path=shot_detach)
        print(f"Captured: {shot_detach}")

        print("\n=== STEP 8: Re-Add Certificate in Cart ===")
        await add_cert_prompt.first.click()
        await page.wait_for_timeout(4000)

        cart_state = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"After Re-Add Cert: Total items in cart={len(cart_state['items'])}")
        assert len(cart_state["items"]) == 2, f"Expected 2 items, got {len(cart_state['items'])}"

        print("\n=== STEP 9: Remove Parent Product (Atomic Zeroing, Zero Orphans) ===")
        remove_product_btn = page.locator("tr[data-attached-cert-key] button.cart-items__remove").first
        await remove_product_btn.click()
        await page.wait_for_timeout(4000)

        cart_state = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"After Atomic Product Removal: Total items={len(cart_state.get('items', []))}")
        assert len(cart_state.get("items", [])) == 0, f"Expected 0 items in cart, got {len(cart_state['items'])}"
        print("Cart is completely empty. Zero orphaned certificates remaining!")

        shot_empty = os.path.join(SCREENSHOT_DIR, "sync_07_cart_empty.png")
        await page.screenshot(path=shot_empty)
        print(f"Captured: {shot_empty}")

        print("\n=== STEP 10: Verify 7-Store PDP CheckCheck Availability ===")
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
            await page.wait_for_timeout(1500)
            chk = page.locator("#checkcheck-addon-checkbox")
            present = await chk.count() > 0
            visible = await chk.is_visible() if present else False
            print(f"[{store}] {path} -> Present: {present}, Visible: {visible}")
            assert present, f"Missing #checkcheck-addon-checkbox on {store} PDP: {url}"

        await browser.close()
        print("\n>>> ALL STEPPER & STOREWIDE VERIFICATIONS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    asyncio.run(test_stepper_synchronization())
