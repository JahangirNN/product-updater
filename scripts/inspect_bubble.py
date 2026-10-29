import asyncio
import json
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='msedge', headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page = await context.new_page()
        await page.goto('https://therareavenue.com/cart')
        
        info = await page.evaluate('''() => {
            const bubbles = Array.from(document.querySelectorAll("[ref='cartBubbleCount'], .cart-bubble__text-count, .cart-bubble, cart-icon"));
            return bubbles.map(b => ({
                tag: b.tagName,
                className: b.className,
                text: b.textContent.trim(),
                html: b.outerHTML.slice(0, 200),
                sessionCount: sessionStorage.getItem('cart-count')
            }));
        }''')
        print(json.dumps(info, indent=2))
        await browser.close()

if __name__ == '__main__':
    asyncio.run(inspect())
