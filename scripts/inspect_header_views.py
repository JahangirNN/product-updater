import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def inspect_header_views():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        breakpoints = [
            ("ipad_mini_768", 768, 1024),
            ("ipad_mini_6_744", 744, 1133),
            ("ipad_portrait_810", 810, 1080),
            ("ipad_mini_landscape_1024", 1024, 768),
            ("desktop_1280", 1280, 800)
        ]

        for name, w, h in breakpoints:
            context = await browser.new_context(
                viewport={"width": w, "height": h},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=(w < 1024),
                has_touch=(w < 1024)
            )
            page = await context.new_page()
            await page.goto("https://therareavenue.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # Header element screenshot
            header = page.locator("#header-component, .header").first
            shot_path = os.path.join(SCREENSHOT_DIR, f"header_strip_{name}.png")
            await header.screenshot(path=shot_path)
            print(f"Captured header strip for {name} ({w}x{h}): {shot_path}")

            # Collect layout diagnostics
            diag = await page.evaluate("""() => {
                const header = document.querySelector('#header-component');
                const row = document.querySelector('.header__row--top');
                const cols = document.querySelector('.header__columns');
                const left = document.querySelector('.header__column--left');
                const right = document.querySelector('.header__column--right');
                const drawer = document.querySelector('.header__drawer');
                const logo = document.querySelector('.header-logo');
                const menu = document.querySelector('header-menu');
                const actions = document.querySelector('header-actions');

                function info(el, label) {
                    if (!el) return { label, exists: false };
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return {
                        label,
                        exists: true,
                        display: s.display,
                        visibility: s.visibility,
                        left: Math.round(r.left),
                        width: Math.round(r.width),
                        right: Math.round(r.right),
                        height: Math.round(r.height),
                        overflowing: r.right > window.innerWidth
                    };
                }

                return {
                    windowW: window.innerWidth,
                    header: info(header, 'header'),
                    cols: info(cols, 'cols'),
                    left: info(left, 'left col'),
                    right: info(right, 'right col'),
                    drawer: info(drawer, 'drawer (hamburger)'),
                    logo: info(logo, 'logo'),
                    menu: info(menu, 'header-menu (desktop nav)'),
                    actions: info(actions, 'actions (cart/account)')
                };
            }""")
            print(f"--- Layout for {name} ({w}px) ---")
            for k, v in diag.items():
                if k != 'windowW':
                    print(f"  {k}: {v}")
            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_header_views())
