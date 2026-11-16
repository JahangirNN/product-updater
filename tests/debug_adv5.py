import asyncio
import json
import sys
import os

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.async_api import async_playwright

async def debug_adv5():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("\n--- Clearing Cart ---")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1000)

        # 1. Add Coach certified
        print("1. Adding Coach certified...")
        await page.goto("https://therareavenue.com/products/pouch-in-signature-canvas")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1500)
        cc = page.locator("#checkcheck-addon-checkbox")
        if not await cc.is_checked():
            await cc.check()
        await page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first.click()
        await page.wait_for_timeout(3500)

        # 2. Add Jomashop uncertified
        print("2. Adding Jomashop uncertified...")
        await page.goto("https://therareavenue.com/products/tissot-carson-watch-t1224071105100")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1500)
        cc = page.locator("#checkcheck-addon-checkbox")
        if await cc.is_checked():
            await cc.uncheck()
        await page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first.click()
        await page.wait_for_timeout(3500)

        # 3. Add MK certified
        print("3. Adding MK certified...")
        await page.goto("https://therareavenue.com/products/cherie-leather-sandal")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(1500)
        cc = page.locator("#checkcheck-addon-checkbox")
        if not await cc.is_checked():
            await cc.check()
        await page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first.click()
        await page.wait_for_timeout(3500)

        # Navigate to /cart
        print("\n--- In /cart ---")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        cart_initial = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"Cart has {len(cart_initial.get('items', []))} items:")
        for idx, it in enumerate(cart_initial.get('items', [])):
            print(f" Item #{idx}: key={it['key']}, title={it['title']}, variant={it['variant_id']}, qty={it['quantity']}, props={it.get('properties')}")

        # Inspect DOM rows
        rows = await page.locator("tr.cart-items__table-row").all()
        print(f"\nRendered DOM table rows ({len(rows)}):")
        for idx, r in enumerate(rows):
            key = await r.get_attribute("data-key")
            var_id = await r.get_attribute("data-variant-id")
            line_idx = await r.get_attribute("data-line-index")
            attached_cert_key = await r.get_attribute("data-attached-cert-key")
            print(f" Row #{idx}: var_id={var_id}, line_idx={line_idx}, key={key}, attached_cert_key={attached_cert_key}")

        # Step Coach up to 2
        print("\n--- Stepping Coach up to 2 ---")
        coach_plus = page.locator("tr[data-variant-id='57530143768742'] button[name='plus']").first
        print(f"Coach plus count: {await coach_plus.count()}")
        if await coach_plus.count() > 0:
            await coach_plus.click()
            await page.wait_for_timeout(4000)

        cart_after_coach = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print("\nCart after stepping Coach:")
        for idx, it in enumerate(cart_after_coach.get('items', [])):
            print(f" Item #{idx}: variant={it['variant_id']}, qty={it['quantity']}, props={it.get('properties')}")

        # Step MK up to 3
        print("\n--- Stepping MK up to 3 ---")
        mk_plus = page.locator("tr[data-variant-id='57546840965286'] button[name='plus']").first
        print(f"MK plus count: {await mk_plus.count()}")
        if await mk_plus.count() > 0:
            await mk_plus.click()
            await page.wait_for_timeout(3500)
            await mk_plus.click()
            await page.wait_for_timeout(4000)

        cart_after_mk = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print("\nCart after stepping MK:")
        for idx, it in enumerate(cart_after_mk.get('items', [])):
            print(f" Item #{idx}: variant={it['variant_id']}, qty={it['quantity']}, props={it.get('properties')}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_adv5())
