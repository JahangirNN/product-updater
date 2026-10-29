import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def inspect_header():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        viewports = [
            ("ipad_mini_portrait_768", 768, 1024),
            ("ipad_mini_6_portrait_744", 744, 1133),
            ("ipad_mini_portrait_820", 820, 1180),
            ("ipad_mini_landscape_1024", 1024, 768),
        ]

        for name, width, height in viewports:
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()
            await page.goto("https://therareavenue.com/")
            await page.wait_for_timeout(2500)

            # Screenshot header area
            header = page.locator("header, #header-group, .header").first
            header_shot = os.path.join(SCREENSHOT_DIR, f"header_{name}.png")
            await page.screenshot(path=header_shot)
            print(f"Captured full page at {width}x{height}: {header_shot}")

            # Inspect elements in header
            info = await page.evaluate("""() => {
                const header = document.querySelector('header, #header-group, .header');
                if (!header) return { error: 'No header found' };
                const rect = header.getBoundingClientRect();
                const children = Array.from(header.querySelectorAll('*')).map(el => {
                    const r = el.getBoundingClientRect();
                    return {
                        tag: el.tagName,
                        className: el.className,
                        id: el.id,
                        rect: { top: r.top, left: r.left, width: r.width, height: r.height, right: r.right },
                        overflowing: r.right > window.innerWidth
                    };
                }).filter(x => x.overflowing || (x.className && typeof x.className === 'string' && (x.className.includes('nav') || x.className.includes('menu') || x.className.includes('logo'))));
                return {
                    windowWidth: window.innerWidth,
                    headerHeight: rect.height,
                    headerWidth: rect.width,
                    items: children.slice(0, 15)
                };
            }""")
            print(f"Viewport {width}x{height} header metrics:", info)
            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_header())
