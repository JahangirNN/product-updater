import asyncio
import json
from playwright.async_api import async_playwright

async def debug_keyboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        requests = []
        page.on("request", lambda req: requests.append(f"{req.method} {req.url}"))
        page.on("response", lambda res: requests.append(f"RESP {res.status} {res.url}"))
        page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
        page.on("console", lambda msg: print(f"CONSOLE: {msg.type}: {msg.text}"))

        print("\n--- Clearing Cart ---")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(1000)

        print("\n--- Adding Coach with CheckCheck ---")
        await page.goto("https://therareavenue.com/products/pouch-in-signature-canvas")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        cc = page.locator("#checkcheck-addon-checkbox")
        await cc.scroll_into_view_if_needed()
        if not await cc.is_checked():
            await cc.check()

        atc = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await atc.click()
        await page.wait_for_timeout(4000)

        print("\n--- Navigating to /cart ---")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        cart_initial = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"Initial cart items: {len(cart_initial.get('items', []))}")
        for it in cart_initial.get('items', []):
            print(f"  - {it['title']} (variant {it['variant_id']}), qty={it['quantity']}, line={it.get('index')}")

        # Locate inputs
        inputs = await page.locator("input[name='updates[]'], .quantity-selector input[type='number'], input.quantity__input").all()
        print(f"Found {len(inputs)} quantity inputs on /cart")
        for idx, inp in enumerate(inputs):
            outer = await inp.evaluate("el => el.outerHTML")
            val = await inp.evaluate("el => el.value")
            parent_form = await inp.evaluate("el => el.form ? el.form.outerHTML.slice(0, 100) : 'none'")
            print(f" Input #{idx}: val='{val}', outerHTML={outer}")
            print(f"    Form: {parent_form}")

        # Now test typing 5
        print("\n--- Testing typing '5' into first input ---")
        requests.clear()
        target_inp = inputs[0]
        await target_inp.click()
        await target_inp.fill("5")
        print(f"Value immediately after fill: {await target_inp.evaluate('el => el.value')}")
        await target_inp.dispatch_event("change")
        print("Dispatched change event")
        await page.wait_for_timeout(4000)

        print(f"Network requests after change: {requests}")
        cart_after_change = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"Cart after change: {len(cart_after_change.get('items', []))} items")
        for it in cart_after_change.get('items', []):
            print(f"  - {it['title']} (variant {it['variant_id']}), qty={it['quantity']}")

        # Now test Enter
        print("\n--- Testing pressing Enter ---")
        requests.clear()
        await target_inp.press("Enter")
        await page.wait_for_timeout(4000)
        print(f"Network requests after Enter: {requests}")
        cart_after_enter = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print(f"Cart after Enter: {len(cart_after_enter.get('items', []))} items")
        for it in cart_after_enter.get('items', []):
            print(f"  - {it['title']} (variant {it['variant_id']}), qty={it['quantity']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_keyboard())
