import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        
        info = await page.evaluate("""() => {
            const el = document.querySelector('cart-items-component');
            if (!el) return 'No cart-items-component';
            const proto = Object.getPrototypeOf(el);
            return {
                methods: Object.getOwnPropertyNames(proto),
                id: el.id,
                dataset: el.dataset
            };
        }""")
        print("Cart items component proto:", info)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
