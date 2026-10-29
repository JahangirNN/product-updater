import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_stepper_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

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

        row_html = await page.evaluate("""() => {
            const row = document.querySelector('tr[data-attached-cert-key]');
            if (!row) return { error: 'No row with data-attached-cert-key' };
            
            const qtyControls = row.querySelector('.cart-items__quantity-controls');
            const btns = Array.from(qtyControls.querySelectorAll('button')).map(b => ({
                tag: b.tagName,
                name: b.getAttribute('name'),
                aria: b.getAttribute('aria-label'),
                classes: b.className,
                onClickAttr: b.getAttribute('on:click'),
                disabled: b.disabled,
                html: b.outerHTML
            }));
            
            const input = qtyControls.querySelector('input');
            
            return {
                rowKey: row.dataset.key,
                attachedCertKey: row.dataset.attachedCertKey,
                qtyControlsHtml: qtyControls.innerHTML,
                buttons: btns,
                inputAttrs: input ? {
                    value: input.value,
                    name: input.getAttribute('name'),
                    cartLine: input.getAttribute('data-cart-line'),
                    classes: input.className
                } : null
            };
        }""")
        print("Row HTML info:\n", json.dumps(row_html, indent=2))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_stepper_html())
