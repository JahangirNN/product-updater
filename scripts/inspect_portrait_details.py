import asyncio
from playwright.async_api import async_playwright

async def inspect_portrait():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='msedge', headless=True)
        ctx = await browser.new_context(
            viewport={'width': 1024, 'height': 768},
            user_agent='Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            is_mobile=True,
            has_touch=True
        )
        page = await ctx.new_page()
        await page.goto('https://therareavenue.com/', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)

        details = await page.evaluate("""() => {
            const h = document.querySelector('#header-component');
            const cols = document.querySelector('.header__columns');
            const drawer = document.querySelector('.header__drawer');
            const search = document.querySelector('.search-action');
            const logo = document.querySelector('.header-logo');
            const actions = document.querySelector('header-actions');
            const account = document.querySelector('.account-button');
            const menu = document.querySelector('header-menu');
            const cart = document.querySelector('.action__cart, button[data-testid="cart-drawer-trigger"]');
            
            const getBox = el => el ? {
                tag: el.tagName,
                cls: el.className,
                rect: el.getBoundingClientRect(),
                cs: {
                    display: window.getComputedStyle(el).display,
                    visibility: window.getComputedStyle(el).visibility,
                    opacity: window.getComputedStyle(el).opacity,
                    padding: window.getComputedStyle(el).padding,
                    margin: window.getComputedStyle(el).margin,
                }
            } : null;

            return {
                h: getBox(h),
                cols: getBox(cols),
                drawer: getBox(drawer),
                search: getBox(search),
                logo: getBox(logo),
                actions: getBox(actions),
                menu: getBox(menu),
                account: getBox(account),
                cart: getBox(cart),
            };
        }""")
        for k, v in details.items():
            print(f"{k}:", v['rect'] if v else 'None')
        await browser.close()

if __name__ == '__main__':
    asyncio.run(inspect_portrait())
