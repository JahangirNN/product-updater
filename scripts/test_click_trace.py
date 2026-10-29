import asyncio
import json
from playwright.async_api import async_playwright

async def test_trace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[BROWSER CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[BROWSER ERROR] {err}"))

        print("1. Adding watch to cart...")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.goto("https://therareavenue.com/products/tissot-carson-watch-t1224071105100")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        cc_box = page.locator("#checkcheck-addon-checkbox")
        await cc_box.check()
        await page.locator("product-form-component button[type='submit']").first.click()
        await page.wait_for_timeout(3500)

        print("2. Navigating to /cart...")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        trace = await page.evaluate("""() => {
            const logs = [];
            const plus = document.querySelector('tr[data-attached-cert-key] button[name="plus"]');
            const sel = document.querySelector('tr[data-attached-cert-key] cart-quantity-selector-component');
            const comp = document.querySelector('cart-items-component');
            const input = sel ? sel.querySelector('input') : null;
            
            logs.push({ step: 'init', hasPlus: !!plus, hasSel: !!sel, hasComp: !!comp, inputVal: input ? input.value : null });
            
            // Listen to all events
            const eventNames = [
                'click', 'change', 'input',
                'theme:quantity-selector:update',
                'QuantitySelectorUpdateEvent',
                'cart:update',
                'shopify:cart:lines-update'
            ];
            
            for (const name of eventNames) {
                document.addEventListener(name, (e) => {
                    logs.push({
                        event: name,
                        type: e.type,
                        target: e.target ? (e.target.tagName + (e.target.className ? '.' + e.target.className : '')) : null,
                        detail: e.detail
                    });
                });
            }
            
            // Dispatch click on plus
            if (plus) {
                plus.click();
            }
            
            logs.push({ step: 'after_click', inputVal: input ? input.value : null });
            return logs;
        }""")
        print("Trace logs:\n", json.dumps(trace, indent=2))

        await page.wait_for_timeout(3000)
        cart = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print("Cart items after 3s:", [(it["title"], it["quantity"]) for it in cart.get("items", [])])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_trace())
