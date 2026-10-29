import asyncio
import sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect_buttons():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        await page.goto("https://therareavenue.com/products/versace-greca-sphere-quartz-silver-dial-ladies-watch-box-set-ve9c00324")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        buttons = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).map(b => ({
                text: b.textContent.trim(),
                name: b.name,
                type: b.type,
                className: b.className,
                id: b.id,
                ref: b.getAttribute('ref')
            }));
        }""")
        print("Buttons found on PDP:")
        for b in buttons:
            if 'cart' in b['text'].lower() or 'add' in b['text'].lower() or b['name'] == 'add' or 'cart' in b['className'].lower():
                print("  ", b)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_buttons())
