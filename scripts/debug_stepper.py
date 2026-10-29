import asyncio
import json
from playwright.async_api import async_playwright

async def debug_stepper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))
        page.on("request", lambda req: print(f"[REQ] {req.method} {req.url}") if "cart" in req.url else None)
        page.on("response", lambda res: print(f"[RES {res.status}] {res.url}") if "cart" in res.url else None)

        print("Navigating to /cart...")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        scripts = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('script[src]')).map(s => s.src).filter(s => s.includes('component-cart') || s.includes('cart'));
        }""")
        print("Cart scripts loaded on page:", scripts)

        selector_info = await page.evaluate("""() => {
            const sel = document.querySelector('cart-quantity-selector-component');
            const inp = sel ? sel.querySelector('input') : null;
            const btn = sel ? sel.querySelector('button[name="plus"]') : null;
            return {
                hasSelector: !!sel,
                selectorTag: sel ? sel.tagName : null,
                hasInput: !!inp,
                inputValue: inp ? inp.value : null,
                inputCartLine: inp ? inp.dataset.cartLine : null,
                hasBtn: !!btn,
                btnDisabled: btn ? btn.disabled : null
            };
        }""")
        print("Selector info:", selector_info)

        plus = page.locator("cart-quantity-selector-component button[name='plus']").first
        print("Clicking plus button via Playwright...")
        await plus.click()
        await page.wait_for_timeout(4000)

        cart = await page.evaluate("async () => (await fetch('/cart.js')).json()")
        print("Cart after plus click:", [(it["title"], it["quantity"]) for it in cart.get("items", [])])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_stepper())
