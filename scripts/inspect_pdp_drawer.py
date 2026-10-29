import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        await page.goto("https://therareavenue.com/products/tissot-carson-watch-t1224071105100")
        await page.wait_for_load_state("domcontentloaded")
        
        info = await page.evaluate("""() => {
            const drawerCartItems = document.querySelector('theme-drawer cart-items-component, #cart-drawer cart-items-component, cart-items-component');
            return {
                found: !!drawerCartItems,
                parent: drawerCartItems?.parentElement?.tagName,
                sectionId: drawerCartItems?.dataset?.sectionId
            };
        }""")
        print("Drawer cart items component:", info)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
