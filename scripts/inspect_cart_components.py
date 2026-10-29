import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_load_state("domcontentloaded")
        
        info = await page.evaluate("""() => {
            const defined = [];
            for (const tag of ['cart-items-component', 'cart-drawer-component', 'theme-drawer']) {
                defined.push({ tag, isDefined: !!customElements.get(tag) });
            }
            return {
                defined,
                themeRoutes: window.Theme?.routes || null
            };
        }""")
        print("Inspection info:", info)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
