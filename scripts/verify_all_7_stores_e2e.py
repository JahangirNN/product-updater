"""
End-to-End Browser & Session Verification Suite across all 7 Stores
Target: The Rare Avenue Live Storefront (https://therareavenue.com)
Active Horizon Theme: gid://shopify/OnlineStoreTheme/198751387814

Tests:
1. Coach Wallet Swatch Click & Add to Cart + Cart Drawer Auto-Open Assertion
2. Jomashop Watch + CheckCheck Addon (Qty=1: 1 watch + 1 certificate = 2 items, NOT 2 watches)
3. Jomashop Watch + CheckCheck Addon Multi-Quantity (Qty=2: 2 watches + 2 certificates = 4 items)
4. Michael Kors (Cherie Leather Sandal) size option click & cart add
5. JW PEI (Hana Large Tote Bag) swatch click & cart add
6. Nordstrom (Project Transport Zip Sneaker) size click & cart add
7. JD Sports (Women's Nike Dunk Low) size click & cart add
8. Foot Locker (adidas Originals Handball Spezial Loafers) size click & cart add
"""
import sys
import os
import json
import asyncio
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.async_api import async_playwright

BASE_URL = "https://therareavenue.com"

async def run_e2e_verification():
    print("=" * 80)
    print("STARTING 7-STORE END-TO-END STOREFRONT VERIFICATION (SKEPTICAL REVIEW RUN)")
    print(f"Base Storefront: {BASE_URL}")
    print("=" * 80)

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # In-browser session helpers (immune to Cloudflare challenges)
        async def clear_cart():
            await page.evaluate('() => fetch("/cart/clear.js", { method: "POST" }).then(r => r.json())')
            await asyncio.sleep(0.5)

        async def get_cart():
            return await page.evaluate('() => fetch("/cart.js").then(r => r.json())')

        # ---------------------------------------------------------------------
        # TEST 1: COACH WALLET SWATCH SELECTION & ADD TO CART & DRAWER AUTO-OPEN
        # ---------------------------------------------------------------------
        print("\n--- TEST 1: Coach Wallet Swatch Selection, Add to Cart & Drawer Auto-Open ---")
        try:
            await page.goto(f"{BASE_URL}/products/id-wallet-in-signature-canvas", wait_until="domcontentloaded")
            await page.wait_for_selector('variant-picker', timeout=10000)
            await clear_cart()

            # Check initial variant id
            initial_var_id = await page.eval_on_selector('form[action*="/cart/add"] input[name="id"]', 'el => el.value')
            print(f"  [Coach] Initial variant ID in form: {initial_var_id}")

            # Click swatch "Charcoal/Black"
            swatch_input = page.locator('input[type="radio"][value="Charcoal/Black"]')
            await swatch_input.scroll_into_view_if_needed()
            await swatch_input.click(force=True)
            await asyncio.sleep(0.8)

            new_var_id = await page.eval_on_selector('form[action*="/cart/add"] input[name="id"]', 'el => el.value')
            print(f"  [Coach] After swatch click variant ID: {new_var_id}")
            assert new_var_id == "57534511448230", f"Expected Charcoal/Black variant 57534511448230, got '{new_var_id}'"

            # Click Add to Cart
            add_button = page.locator('.buy-buttons [type="submit"], product-form-component button[name="add"], .buy-buttons button').first
            async with page.expect_response(lambda r: "/cart/add" in r.url, timeout=10000) as resp_info:
                await add_button.click()
            resp = await resp_info.value
            print(f"  [Coach] /cart/add response status: {resp.status}")
            assert resp.status == 200, f"/cart/add returned status {resp.status}"

            await asyncio.sleep(1.5)

            # Assert Cart Drawer auto-opened
            drawer_state = await page.evaluate('''() => {
                const drawer = document.querySelector('cart-drawer-component');
                const themeDrawer = document.querySelector('theme-drawer#cart-drawer');
                const dialog = themeDrawer ? themeDrawer.querySelector('dialog') : null;
                return {
                    autoOpenAttr: drawer?.hasAttribute('auto-open') || false,
                    themeDrawerOpen: themeDrawer?.hasAttribute('open') || false,
                    dialogOpen: dialog?.open || false
                };
            }''')
            print(f"  [Coach] Cart Drawer State: {drawer_state}")
            assert drawer_state["autoOpenAttr"] is True, "cart-drawer-component missing auto-open attribute"
            assert drawer_state["themeDrawerOpen"] is True or drawer_state["dialogOpen"] is True, "Cart drawer failed to auto-open"

            # Verify cart content
            cart_data = await get_cart()
            assert cart_data["item_count"] == 1, f"Expected 1 item in cart, got {cart_data['item_count']}"
            item = cart_data["items"][0]
            assert str(item["variant_id"]) == "57534511448230", f"Expected variant 57534511448230, got {item['variant_id']}"
            price_str = f"{item['price']/100:.2f}"
            print(f"  [Coach] PASS! Added '{item['title']}' (Variant {item['variant_id']}) price: Rs. {price_str}, Drawer OPEN: Yes")
            results.append({"test": "1. Coach Wallet Swatch & Drawer Auto-Open", "status": "PASS", "details": f"Variant {item['variant_id']} (Rs. {price_str}), Drawer Opened"})
        except Exception as e:
            print(f"  [Coach] FAIL: {e}")
            results.append({"test": "1. Coach Wallet Swatch & Drawer Auto-Open", "status": "FAIL", "error": str(e)})

        # ---------------------------------------------------------------------
        # TEST 2: JOMASHOP WATCH + CHECKCHECK ADDON (QTY 1 SINGLE ATOMIC BUNDLE)
        # ---------------------------------------------------------------------
        print("\n--- TEST 2: Jomashop Watch + CheckCheck Addon Bundle (Qty=1) ---")
        try:
            await page.goto(f"{BASE_URL}/products/versace-greca-jewel-quartz-green-dial-ladies-watch-vewca0224", wait_until="domcontentloaded")
            await page.wait_for_selector('#checkcheck-addon-checkbox', timeout=10000)
            await clear_cart()

            watch_var_id = await page.eval_on_selector('form[action*="/cart/add"] input[name="id"]', 'el => el.value')
            print(f"  [Watch Qty 1] Watch variant ID: {watch_var_id}")
            assert watch_var_id == "57514246340774", f"Unexpected watch variant ID: {watch_var_id}"

            # Toggle CheckCheck checkbox
            cc_checkbox = page.locator('#checkcheck-addon-checkbox')
            await cc_checkbox.scroll_into_view_if_needed()
            await cc_checkbox.check()
            is_checked = await cc_checkbox.is_checked()
            print(f"  [Watch Qty 1] CheckCheck checkbox is_checked: {is_checked}")
            assert is_checked is True, "CheckCheck checkbox should be checked"

            # Click Add to Cart
            add_button = page.locator('.buy-buttons [type="submit"], product-form-component button[name="add"], .buy-buttons button').first
            async with page.expect_response(lambda r: "/cart/add" in r.url, timeout=10000) as resp_info:
                await add_button.click()
            resp = await resp_info.value
            print(f"  [Watch Qty 1] /cart/add response status: {resp.status}")
            assert resp.status == 200, f"/cart/add returned status {resp.status}"

            await asyncio.sleep(1.0)
            cart_data = await get_cart()
            items = cart_data["items"]
            print(f"  [Watch Qty 1] Cart line items: {len(items)}, total item count: {cart_data['item_count']}")

            watch_items = [it for it in items if str(it["variant_id"]) == "57514246340774"]
            cc_items = [it for it in items if str(it["variant_id"]) == "57721101779110"]

            assert len(watch_items) == 1, f"Expected 1 watch line item, got {len(watch_items)}"
            assert watch_items[0]["quantity"] == 1, f"Expected watch quantity 1, got {watch_items[0]['quantity']} (Bug was 2 watches!)"
            assert len(cc_items) == 1, f"Expected 1 CheckCheck line item, got {len(cc_items)}"
            assert cc_items[0]["quantity"] == 1, f"Expected CheckCheck quantity 1, got {cc_items[0]['quantity']}"
            assert cc_items[0]["price"] == 69900, f"Expected CheckCheck price Rs. 699.00 (69900 paise), got {cc_items[0]['price']}"
            assert watch_items[0]["properties"].get("_checkcheck_certified") == "true", "Watch missing _checkcheck_certified property"

            print(f"  [Watch Qty 1] PASS! Exactly 1 Watch + 1 Certificate (Price: Rs. {cc_items[0]['price']/100})")
            results.append({"test": "2. Watch + CheckCheck Bundle (Qty=1)", "status": "PASS", "details": f"1 Watch + 1 CheckCheck Cert (Rs. {cc_items[0]['price']/100})"})
        except Exception as e:
            print(f"  [Watch Qty 1] FAIL: {e}")
            results.append({"test": "2. Watch + CheckCheck Bundle (Qty=1)", "status": "FAIL", "error": str(e)})

        # ---------------------------------------------------------------------
        # TEST 3: JOMASHOP WATCH + CHECKCHECK MULTI-QUANTITY (QTY 2)
        # ---------------------------------------------------------------------
        print("\n--- TEST 3: Jomashop Watch + CheckCheck Multi-Quantity (Qty=2) ---")
        try:
            await page.goto(f"{BASE_URL}/products/versace-greca-jewel-quartz-green-dial-ladies-watch-vewca0224", wait_until="domcontentloaded")
            await page.wait_for_selector('#checkcheck-addon-checkbox', timeout=10000)
            await clear_cart()

            # Set quantity = 2
            qty_input = page.locator('quantity-selector-component input, input[name="quantity"]').first
            if await qty_input.count() > 0:
                await qty_input.fill("2")
                await qty_input.dispatch_event("change")
                print("  [Watch Qty 2] Quantity changed to 2")

            cc_checkbox = page.locator('#checkcheck-addon-checkbox')
            await cc_checkbox.check()

            async with page.expect_response(lambda r: "/cart/add" in r.url, timeout=10000) as resp_info:
                await add_button.click()
            resp = await resp_info.value
            assert resp.status == 200, f"/cart/add returned status {resp.status}"

            await asyncio.sleep(1.0)
            cart_data = await get_cart()
            items = cart_data["items"]
            watch_items = [it for it in items if str(it["variant_id"]) == "57514246340774"]
            cc_items = [it for it in items if str(it["variant_id"]) == "57721101779110"]

            assert len(watch_items) == 1 and watch_items[0]["quantity"] == 2, f"Expected 2 watches, got {watch_items[0]['quantity'] if watch_items else 0}"
            assert len(cc_items) == 1 and cc_items[0]["quantity"] == 2, f"Expected 2 CheckCheck certificates, got {cc_items[0]['quantity'] if cc_items else 0}"
            assert cart_data["item_count"] == 4, f"Expected total 4 items, got {cart_data['item_count']}"

            print(f"  [Watch Qty 2] PASS! Multi-qty correctly added: 2 Watches + 2 Certificates (Total 4 items)")
            results.append({"test": "3. Watch + CheckCheck Multi-Qty (Qty=2)", "status": "PASS", "details": "2 Watches + 2 Certificates"})
        except Exception as e:
            print(f"  [Watch Qty 2] FAIL: {e}")
            results.append({"test": "3. Watch + CheckCheck Multi-Qty (Qty=2)", "status": "FAIL", "error": str(e)})

        # ---------------------------------------------------------------------
        # TEST 4: MICHAEL KORS (Cherie Leather Sandal)
        # ---------------------------------------------------------------------
        print("\n--- TEST 4: Michael Kors (Cherie Leather Sandal) ---")
        try:
            await page.goto(f"{BASE_URL}/products/cherie-leather-sandal", wait_until="domcontentloaded")
            await page.wait_for_selector('variant-picker', timeout=10000)
            await clear_cart()

            size_radio = page.locator('input[type="radio"][value="US 8.5 / UK 6.5"]')
            await size_radio.scroll_into_view_if_needed()
            await size_radio.click(force=True)
            await asyncio.sleep(0.8)

            var_id = await page.eval_on_selector('form[action*="/cart/add"] input[name="id"]', 'el => el.value')
            print(f"  [MK] Selected variant ID: {var_id}")
            assert var_id == "57546841129126", f"Expected variant 57546841129126, got {var_id}"

            add_button = page.locator('.buy-buttons [type="submit"], product-form-component button[name="add"], .buy-buttons button').first
            async with page.expect_response(lambda r: "/cart/add" in r.url, timeout=10000) as resp_info:
                await add_button.click()
            resp = await resp_info.value
            assert resp.status == 200, f"/cart/add status {resp.status}"

            await asyncio.sleep(1.0)
            cart_data = await get_cart()
            assert cart_data["item_count"] == 1
            item = cart_data["items"][0]
            price_int = int(item['price'] / 100)
            assert str(price_int).endswith("99"), f"Expected price ending in 99 charm, got {price_int}"
            print(f"  [MK] PASS! Added '{item['title']}' variant {item['variant_id']}, price: Rs. {price_int}")
            results.append({"test": "4. Michael Kors Sandal", "status": "PASS", "details": f"Variant {item['variant_id']}, price: Rs. {price_int}"})
        except Exception as e:
            print(f"  [MK] FAIL: {e}")
            results.append({"test": "4. Michael Kors Sandal", "status": "FAIL", "error": str(e)})

        # ---------------------------------------------------------------------
        # TEST 5: JW PEI (Hana Large Tote Bag)
        # ---------------------------------------------------------------------
        print("\n--- TEST 5: JW PEI (Hana Large Tote Bag) ---")
        try:
            await page.goto(f"{BASE_URL}/products/hana-large-tote-bag-pink", wait_until="domcontentloaded")
            await page.wait_for_selector('variant-picker', timeout=10000)
            await clear_cart()

            swatch = page.locator('input[type="radio"][value="Dark Brown"]')
            await swatch.scroll_into_view_if_needed()
            await swatch.click(force=True)
            await asyncio.sleep(0.8)

            var_id = await page.eval_on_selector('form[action*="/cart/add"] input[name="id"]', 'el => el.value')
            print(f"  [JW PEI] Selected variant ID: {var_id}")
            assert var_id == "57534237704358", f"Expected variant 57534237704358, got {var_id}"

            add_button = page.locator('.buy-buttons [type="submit"], product-form-component button[name="add"], .buy-buttons button').first
            async with page.expect_response(lambda r: "/cart/add" in r.url, timeout=10000) as resp_info:
                await add_button.click()
            resp = await resp_info.value
            assert resp.status == 200, f"/cart/add status {resp.status}"

            await asyncio.sleep(1.0)
            cart_data = await get_cart()
            assert cart_data["item_count"] == 1
            item = cart_data["items"][0]
            price_int = int(item['price'] / 100)
            assert str(price_int).endswith("99"), f"Expected price ending in 99 charm, got {price_int}"
            print(f"  [JW PEI] PASS! Added '{item['title']}' variant {item['variant_id']}, price: Rs. {price_int}")
            results.append({"test": "5. JW PEI Tote Bag", "status": "PASS", "details": f"Variant {item['variant_id']}, price: Rs. {price_int}"})
        except Exception as e:
            print(f"  [JW PEI] FAIL: {e}")
            results.append({"test": "5. JW PEI Tote Bag", "status": "FAIL", "error": str(e)})

        # ---------------------------------------------------------------------
        # TEST 6: NORDSTROM (Project Transport Zip Sneaker)
        # ---------------------------------------------------------------------
        print("\n--- TEST 6: Nordstrom (Project Transport Zip Sneaker) ---")
        try:
            await page.goto(f"{BASE_URL}/products/project-transport-zip-sneaker-men", wait_until="domcontentloaded")
            await page.wait_for_selector('variant-picker', timeout=10000)
            await clear_cart()

            size_btn = page.locator('input[type="radio"][value="UK 10.5"]')
            await size_btn.scroll_into_view_if_needed()
            await size_btn.click(force=True)
            await asyncio.sleep(0.8)

            var_id = await page.eval_on_selector('form[action*="/cart/add"] input[name="id"]', 'el => el.value')
            print(f"  [Nordstrom] Selected variant ID: {var_id}")
            assert var_id == "57582278017190", f"Expected variant 57582278017190, got {var_id}"

            add_button = page.locator('.buy-buttons [type="submit"], product-form-component button[name="add"], .buy-buttons button').first
            async with page.expect_response(lambda r: "/cart/add" in r.url, timeout=10000) as resp_info:
                await add_button.click()
            resp = await resp_info.value
            assert resp.status == 200, f"/cart/add status {resp.status}"

            await asyncio.sleep(1.0)
            cart_data = await get_cart()
            assert cart_data["item_count"] == 1
            item = cart_data["items"][0]
            price_int = int(item['price'] / 100)
            assert str(price_int).endswith("99"), f"Expected price ending in 99 charm, got {price_int}"
            print(f"  [Nordstrom] PASS! Added '{item['title']}' variant {item['variant_id']}, price: Rs. {price_int}")
            results.append({"test": "6. Nordstrom Sneaker", "status": "PASS", "details": f"Variant {item['variant_id']}, price: Rs. {price_int}"})
        except Exception as e:
            print(f"  [Nordstrom] FAIL: {e}")
            results.append({"test": "6. Nordstrom Sneaker", "status": "FAIL", "error": str(e)})

        # ---------------------------------------------------------------------
        # TEST 7: JD SPORTS (Women's Nike Dunk Low)
        # ---------------------------------------------------------------------
        print("\n--- TEST 7: JD Sports (Women's Nike Dunk Low) ---")
        try:
            await page.goto(f"{BASE_URL}/products/womens-nike-dunk-low-patent-leather-casual-shoes-pink-foam-black-white-3337873", wait_until="domcontentloaded")
            await page.wait_for_selector('variant-picker', timeout=10000)
            await clear_cart()

            size_btn = page.locator('input[type="radio"][value="UK 4"]')
            await size_btn.scroll_into_view_if_needed()
            await size_btn.click(force=True)
            await asyncio.sleep(0.8)

            var_id = await page.eval_on_selector('form[action*="/cart/add"] input[name="id"]', 'el => el.value')
            print(f"  [JD Sports] Selected variant ID: {var_id}")
            assert var_id == "57581775847590", f"Expected variant 57581775847590, got {var_id}"

            add_button = page.locator('.buy-buttons [type="submit"], product-form-component button[name="add"], .buy-buttons button').first
            async with page.expect_response(lambda r: "/cart/add" in r.url, timeout=10000) as resp_info:
                await add_button.click()
            resp = await resp_info.value
            assert resp.status == 200, f"/cart/add status {resp.status}"

            await asyncio.sleep(1.0)
            cart_data = await get_cart()
            assert cart_data["item_count"] == 1
            item = cart_data["items"][0]
            price_int = int(item['price'] / 100)
            assert str(price_int).endswith("99"), f"Expected price ending in 99 charm, got {price_int}"
            print(f"  [JD Sports] PASS! Added '{item['title']}' variant {item['variant_id']}, price: Rs. {price_int}")
            results.append({"test": "7. JD Sports Nike Dunk Low", "status": "PASS", "details": f"Variant {item['variant_id']}, price: Rs. {price_int}"})
        except Exception as e:
            print(f"  [JD Sports] FAIL: {e}")
            results.append({"test": "7. JD Sports Nike Dunk Low", "status": "FAIL", "error": str(e)})

        # ---------------------------------------------------------------------
        # TEST 8: FOOT LOCKER (adidas Originals Handball Spezial Loafers)
        # ---------------------------------------------------------------------
        print("\n--- TEST 8: Foot Locker (adidas Originals Handball Spezial Loafers) ---")
        try:
            await page.goto(f"{BASE_URL}/products/adidas-originals-handball-spezial-loafers-women-s-maroon-maroon-kk2780", wait_until="domcontentloaded")
            await page.wait_for_selector('variant-picker', timeout=10000)
            await clear_cart()

            size_btn = page.locator('input[type="radio"][value="UK 5"]')
            await size_btn.scroll_into_view_if_needed()
            await size_btn.click(force=True)
            await asyncio.sleep(0.8)

            var_id = await page.eval_on_selector('form[action*="/cart/add"] input[name="id"]', 'el => el.value')
            print(f"  [Foot Locker] Selected variant ID: {var_id}")
            assert var_id == "57581782925478", f"Expected variant 57581782925478, got {var_id}"

            add_button = page.locator('.buy-buttons [type="submit"], product-form-component button[name="add"], .buy-buttons button').first
            async with page.expect_response(lambda r: "/cart/add" in r.url, timeout=10000) as resp_info:
                await add_button.click()
            resp = await resp_info.value
            assert resp.status == 200, f"/cart/add status {resp.status}"

            await asyncio.sleep(1.0)
            cart_data = await get_cart()
            assert cart_data["item_count"] == 1
            item = cart_data["items"][0]
            price_int = int(item['price'] / 100)
            assert str(price_int).endswith("99"), f"Expected price ending in 99 charm, got {price_int}"
            print(f"  [Foot Locker] PASS! Added '{item['title']}' variant {item['variant_id']}, price: Rs. {price_int}")
            results.append({"test": "8. Foot Locker adidas Spezial", "status": "PASS", "details": f"Variant {item['variant_id']}, price: Rs. {price_int}"})
        except Exception as e:
            print(f"  [Foot Locker] FAIL: {e}")
            results.append({"test": "8. Foot Locker adidas Spezial", "status": "FAIL", "error": str(e)})

        # Final cleanup
        await clear_cart()
        await browser.close()

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY:")
    for r in results:
        status_flag = "[PASS]" if r["status"] == "PASS" else "[FAIL]"
        detail = r.get("details") or r.get("error")
        print(f"  {status_flag} {r['test']}: {detail}")
    print("=" * 80)

    all_passed = all(r["status"] == "PASS" for r in results)
    print(f"OVERALL RESULT: {'ALL PASSED (' + str(len(results)) + '/' + str(len(results)) + ')' if all_passed else 'SOME FAILED'}")
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(run_e2e_verification())
    sys.exit(0 if success else 1)
