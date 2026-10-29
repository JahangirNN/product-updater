import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_events():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()

        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        info = await page.evaluate("""() => {
            const sel = document.querySelector('cart-quantity-selector-component');
            const comp = document.querySelector('cart-items-component');
            
            const customEls = {
                cartQuantitySelector: !!customElements.get('cart-quantity-selector-component'),
                quantitySelector: !!customElements.get('quantity-selector-component'),
                cartItems: !!customElements.get('cart-items-component'),
            };
            
            const input = sel ? sel.querySelector('input') : null;
            const plus = sel ? sel.querySelector('button[name="plus"]') : null;
            
            return {
                customEls,
                selConnected: sel ? sel.isConnected : null,
                compConnected: comp ? comp.isConnected : null,
                inputVal: input ? input.value : null,
                inputCartLine: input ? (input.dataset ? input.dataset.cartLine : null) : null,
                plusExists: !!plus,
                plusDisabled: plus ? plus.disabled : null
            };
        }""")
        print("Inspection result:", json.dumps(info, indent=2))

        # Test triggering click directly in page context and logging event
        click_result = await page.evaluate("""() => {
            const plus = document.querySelector('cart-quantity-selector-component button[name="plus"]');
            if (!plus) return { clicked: false, reason: 'no plus button' };
            
            let eventCaptured = null;
            const listener = (e) => {
                eventCaptured = {
                    type: e.type,
                    bubbles: e.bubbles,
                    cancelable: e.cancelable,
                    detail: e.detail
                };
            };
            
            document.addEventListener('theme:quantity-selector:update', listener);
            document.addEventListener('QuantitySelectorUpdateEvent', listener);
            
            plus.click();
            
            return {
                clicked: true,
                eventCaptured,
                inputValAfterClick: document.querySelector('cart-quantity-selector-component input')?.value
            };
        }""")
        print("Click result:", json.dumps(click_result, indent=2))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_events())
