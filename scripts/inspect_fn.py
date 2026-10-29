import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        
        fn_str = await page.evaluate("""() => {
            const el = document.querySelector('cart-items-component');
            return el?.fetchCartData ? el.fetchCartData.toString() : 'none';
        }""")
        print("fetchCartData source:", fn_str)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
