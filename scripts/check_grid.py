import asyncio
import json
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def check_grid():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        for w, h, label in [(768, 1024, "iPad Mini Portrait (768px)"), (744, 1133, "iPad Mini 6 Portrait (744px)"), (1024, 768, "iPad Mini Landscape (1024px)")]:
            context = await browser.new_context(
                viewport={"width": w, "height": h},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()
            await page.goto("https://therareavenue.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            data = await page.evaluate("""() => {
                const cols = document.querySelector('.header__columns');
                const row = document.querySelector('.header__row--top');
                const header = document.querySelector('#header-component');
                const csCols = window.getComputedStyle(cols);
                const csRow = window.getComputedStyle(row);

                // Collect bounding rects of all direct children or key components
                const items = Array.from(document.querySelectorAll('#header-component *')).filter(el => {
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden' && (
                        el.classList.contains('header__drawer') ||
                        el.classList.contains('header-logo') ||
                        el.classList.contains('header-menu') ||
                        el.classList.contains('header-actions') ||
                        el.classList.contains('search-action') ||
                        el.classList.contains('account-button') ||
                        el.classList.contains('cart-button') ||
                        el.tagName === 'HEADER-DRAWER' ||
                        el.tagName === 'HEADER-MENU' ||
                        el.tagName === 'HEADER-ACTIONS' ||
                        el.tagName === 'SEARCH-BUTTON'
                    );
                }).map(el => {
                    const r = el.getBoundingClientRect();
                    return {
                        tag: el.tagName,
                        class: el.className,
                        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), right: Math.round(r.right) }
                    };
                });

                return {
                    windowW: window.innerWidth,
                    colsGridTemplateColumns: csCols.gridTemplateColumns,
                    colsDisplay: csCols.display,
                    rowDisplay: csRow.display,
                    items
                };
            }""")

            print(f"=== {label} ===")
            print("colsGridTemplateColumns:", data['colsGridTemplateColumns'])
            for it in data['items']:
                print(f"  {it['tag']} ({it['class'][:30]}): {it['rect']}")
            print("="*50)
            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_grid())
