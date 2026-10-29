import asyncio
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def get_header_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        # Test at 768px (iPad Mini portrait)
        context = await browser.new_context(
            viewport={"width": 768, "height": 1024},
            user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()
        await page.goto("https://therareavenue.com/")
        await page.wait_for_timeout(2000)

        html = await page.evaluate("""() => {
            const h = document.querySelector('#header-group') || document.querySelector('header');
            return h ? h.outerHTML : 'Not found';
        }""")
        print("Header Group HTML length:", len(html))
        with open("header_dump_768.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote header_dump_768.html")

        # Now test at 1024px (iPad Mini landscape)
        await page.set_viewport_size({"width": 1024, "height": 768})
        await page.wait_for_timeout(1000)
        html_1024 = await page.evaluate("""() => {
            const h = document.querySelector('#header-group') || document.querySelector('header');
            return h ? h.outerHTML : 'Not found';
        }""")
        print("Header Group 1024 HTML length:", len(html_1024))
        with open("header_dump_1024.html", "w", encoding="utf-8") as f:
            f.write(html_1024)
        print("Wrote header_dump_1024.html")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_header_html())
