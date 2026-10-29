import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_buttons():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        buttons_info = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button[name="plus"], button[name="minus"]')).map((b, i) => {
                const tr = b.closest('tr');
                const drawer = b.closest('cart-drawer-component, [data-cart-drawer]');
                const visible = b.offsetWidth > 0 && b.offsetHeight > 0;
                return {
                    index: i,
                    name: b.getAttribute('name'),
                    classes: b.className,
                    insideTr: !!tr,
                    trKey: tr ? tr.dataset.key : null,
                    insideDrawer: !!drawer,
                    visible,
                    parentTag: b.parentElement ? b.parentElement.tagName : null
                };
            });
            return btns;
        }""")
        print("Buttons on /cart:", json.dumps(buttons_info, indent=2))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_buttons())
