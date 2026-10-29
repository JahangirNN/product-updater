import asyncio
import json
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def check_breakages():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        for w, h, label in [(768, 1024, "iPad Mini Portrait 768px"), (1024, 768, "iPad Mini Landscape 1024px")]:
            context = await browser.new_context(
                viewport={"width": w, "height": h},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()
            await page.goto("https://therareavenue.com/")
            await page.wait_for_timeout(2500)

            details = await page.evaluate("""() => {
                const header = document.querySelector('#header-component');
                const underlay = document.querySelector('.header__underlay');
                const row = document.querySelector('.header__row--top');
                const cols = document.querySelector('.header__columns');
                const drawer = document.querySelector('.header__drawer');
                const logo = document.querySelector('.header-logo');
                const menu = document.querySelector('header-menu');
                const menuInner = document.querySelector('.header-menu__inner');
                const menuList = document.querySelector('.header-menu__list');
                const actions = document.querySelector('header-actions');
                const search = document.querySelector('search-button');
                const cart = document.querySelector('.cart-button, [aria-controls=\"cart-drawer\"], a[href*=\"/cart\"]');
                const account = document.querySelector('.account-button, a[href*=\"/account\"]');

                function b(el, name) {
                    if (!el) return { name, present: false };
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return {
                        name,
                        present: true,
                        display: s.display,
                        visibility: s.visibility,
                        opacity: s.opacity,
                        x: Math.round(r.x),
                        y: Math.round(r.y),
                        w: Math.round(r.width),
                        h: Math.round(r.height),
                        right: Math.round(r.right),
                        overflow: s.overflow
                    };
                }

                return {
                    windowW: window.innerWidth,
                    row: b(row, 'row'),
                    cols: b(cols, 'cols'),
                    drawer: b(drawer, 'drawer (hamburger)'),
                    search: b(search, 'search'),
                    logo: b(logo, 'logo'),
                    menu: b(menu, 'header-menu'),
                    menuInner: b(menuInner, 'menuInner'),
                    menuList: b(menuList, 'menuList'),
                    actions: b(actions, 'actions'),
                    cart: b(cart, 'cart'),
                    account: b(account, 'account')
                };
            }""")
            print(f"=== {label} ===")
            for k, v in details.items():
                print(f"  {k}: {v}")
            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_breakages())
