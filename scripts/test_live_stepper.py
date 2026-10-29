import asyncio
import os
import sys
import json
import urllib.request
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def clear_cart_http():
    req = urllib.request.Request("https://therareavenue.com/cart/clear.js", method="POST", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[HTTP] Cart clear: {resp.status}")
    except Exception as e:
        print(f"[HTTP] Cart clear error: {e}")

async def run_live_stepper_test():
    print("=" * 70)
    print("RUNNING LIVE STOREFRONT STEPPER & CHECKCHECK VERIFICATION")
    print("=" * 70)

    # 1. Clear cart
    clear_cart_http()

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()

        page.on("console", lambda msg: print(f"  [BROWSER {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"  [BROWSER ERROR] {err}"))

        # 2. Open Tissot Watch PDP
        print("\nStep 1: Open Tissot Watch PDP")
        await page.goto("https://therareavenue.com/products/tissot-carson-watch-t1224071105100")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        # 3. Check CheckCheck checkbox
        cc_box = page.locator("#checkcheck-addon-checkbox")
        await cc_box.scroll_into_view_if_needed()
        if not await cc_box.is_checked():
            await cc_box.check()
        print(f"CheckCheck checkbox checked: {await cc_box.is_checked()}")

        # 4. Click Add to Cart
        add_btn = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await add_btn.click()
        print("Clicked Add to Cart, waiting 4s...")
        await page.wait_for_timeout(4000)

        # 5. Open /cart
        print("\nStep 2: Open /cart")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2500)

        cart_initial = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent = next((it for it in cart_initial["items"] if it["variant_id"] != 57721101779110), None)
        cert = next((it for it in cart_initial["items"] if it["variant_id"] == 57721101779110), None)
        print(f"Initial Cart: Total Items={len(cart_initial['items'])}, Total Price=INR {cart_initial['total_price']/100:.2f}")
        print(f"  Parent: '{parent['title'] if parent else None}' qty={parent['quantity'] if parent else None}")
        print(f"  Cert:   '{cert['title'] if cert else None}' qty={cert['quantity'] if cert else None}")
        assert parent and parent["quantity"] == 1, f"Parent quantity should be 1"
        assert cert and cert["quantity"] == 1, f"Certificate quantity should be 1"

        shot_initial = os.path.join(SCREENSHOT_DIR, "live_01_initial_cart.png")
        await page.screenshot(path=shot_initial)
        print(f"Captured: {shot_initial}")

        # 6. Click '+' on stepper
        print("\nStep 3: Click '+' Stepper (1 -> 2)")
        plus_btn = page.locator("tr[data-attached-cert-key] button[name='plus'], button[name='plus']").first
        await plus_btn.scroll_into_view_if_needed()
        await plus_btn.click()
        print("Clicked plus, waiting 4s for network request and DOM update...")
        await page.wait_for_timeout(4000)

        cart_plus = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent_plus = next((it for it in cart_plus["items"] if it["variant_id"] != 57721101779110), None)
        cert_plus = next((it for it in cart_plus["items"] if it["variant_id"] == 57721101779110), None)
        print(f"After '+': Total Price=INR {cart_plus['total_price']/100:.2f}")
        print(f"  Parent: qty={parent_plus['quantity'] if parent_plus else None}")
        print(f"  Cert:   qty={cert_plus['quantity'] if cert_plus else None}")

        shot_plus = os.path.join(SCREENSHOT_DIR, "live_02_increment_2.png")
        await page.screenshot(path=shot_plus)
        print(f"Captured: {shot_plus}")

        assert parent_plus and parent_plus["quantity"] == 2, f"Parent quantity should be 2, got {parent_plus['quantity']}"
        assert cert_plus and cert_plus["quantity"] == 2, f"Certificate quantity should be 2, got {cert_plus['quantity']}"

        # 7. Click '-' on stepper (2 -> 1)
        print("\nStep 4: Click '-' Stepper (2 -> 1)")
        minus_btn = page.locator("tr[data-attached-cert-key] button[name='minus'], button[name='minus']").first
        await minus_btn.scroll_into_view_if_needed()
        await minus_btn.click()
        print("Clicked minus, waiting 4s...")
        await page.wait_for_timeout(4000)

        cart_minus = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        parent_minus = next((it for it in cart_minus["items"] if it["variant_id"] != 57721101779110), None)
        cert_minus = next((it for it in cart_minus["items"] if it["variant_id"] == 57721101779110), None)
        print(f"After '-': Total Price=INR {cart_minus['total_price']/100:.2f}")
        print(f"  Parent: qty={parent_minus['quantity'] if parent_minus else None}")
        print(f"  Cert:   qty={cert_minus['quantity'] if cert_minus else None}")

        shot_minus = os.path.join(SCREENSHOT_DIR, "live_03_decrement_1.png")
        await page.screenshot(path=shot_minus)
        print(f"Captured: {shot_minus}")

        assert parent_minus and parent_minus["quantity"] == 1, f"Parent quantity should be 1, got {parent_minus['quantity']}"
        assert cert_minus and cert_minus["quantity"] == 1, f"Certificate quantity should be 1, got {cert_minus['quantity']}"

        # 8. Single cert detach via [Remove]
        print("\nStep 5: Detach Certificate Only via [Remove]")
        remove_cert_btn = page.locator(".ra-remove-cert-btn").first
        await remove_cert_btn.click()
        print("Clicked [Remove] certificate, waiting 4s...")
        await page.wait_for_timeout(4000)

        cart_detached = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"After Detach: Item count={len(cart_detached['items'])}")
        assert len(cart_detached["items"]) == 1, f"Expected 1 item, got {len(cart_detached['items'])}"
        assert cart_detached["items"][0]["variant_id"] != 57721101779110, "Certificate should be removed"

        add_cert_btn = page.locator(".ra-add-cert-btn")
        print(f"Reverted to '+ Add CheckCheck Certificate': {await add_cert_btn.count() > 0}")
        assert await add_cert_btn.count() > 0, "Card must revert to display '+ Add CheckCheck Certificate'"

        shot_detached = os.path.join(SCREENSHOT_DIR, "live_04_cert_detached.png")
        await page.screenshot(path=shot_detached)
        print(f"Captured: {shot_detached}")

        # 9. Re-Add certificate from cart
        print("\nStep 6: Re-Add Certificate in Cart")
        await add_cert_btn.first.click()
        print("Clicked '+ Add CheckCheck Certificate', waiting 4s...")
        await page.wait_for_timeout(4000)

        cart_readded = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"After Re-Add: Total items={len(cart_readded['items'])}")
        assert len(cart_readded["items"]) == 2, f"Expected 2 items, got {len(cart_readded['items'])}"

        # 10. Atomic removal of parent + cert (Zero Orphans)
        print("\nStep 7: Atomic Removal of Certified Product (Zero Orphans)")
        remove_product_btn = page.locator("tr[data-attached-cert-key] button.cart-items__remove").first
        await remove_product_btn.click()
        print("Clicked remove product, waiting 4s...")
        await page.wait_for_timeout(4000)

        cart_empty = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"After Atomic Product Removal: Total items={len(cart_empty.get('items', []))}")
        assert len(cart_empty.get("items", [])) == 0, f"Expected empty cart, got {len(cart_empty.get('items', []))}"

        shot_empty = os.path.join(SCREENSHOT_DIR, "live_05_cart_empty.png")
        await page.screenshot(path=shot_empty)
        print(f"Captured: {shot_empty}")

        # 11. Verify 7-Store PDP CheckCheck Availability
        print("\nStep 8: Verify CheckCheck Widget Across Sample PDPs of All 7 Stores")
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
            print(f"  [{store}] {path} -> Present: {present}, Visible: {visible}")
            assert present, f"Missing #checkcheck-addon-checkbox on {store} PDP: {url}"

        await browser.close()
        print("\n" + "=" * 70)
        print("SUCCESS! ALL LIVE STOREFRONT TESTS PASSED PERFECTLY!")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_live_stepper_test())
