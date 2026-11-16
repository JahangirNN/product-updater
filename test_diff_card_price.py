import asyncio
import os
import time
from playwright.async_api import async_playwright

async def run():
    print("Testing PLP card with different variant prices...", flush=True)
    out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        
        url = f"https://therareavenue.com/search?q=carey+crossbody+bag&v={int(time.time())}"
        print(f"Navigating to {url}...", flush=True)
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2500)

        card = page.locator('product-card, .product-card').first
        if await card.count() > 0:
            swatches = await card.locator('.luxury-card__color-btn').all()
            print(f"Found {len(swatches)} swatches on search card")
            for s in swatches:
                title = await s.get_attribute('title')
                price = await s.get_attribute('data-price')
                print(f"  - Swatch: {title} | Price: {price}")

            # Click a swatch
            if len(swatches) >= 2:
                s1 = swatches[0]
                s2 = swatches[1]
                t1 = await s1.get_attribute('title')
                p1 = await s1.get_attribute('data-price')
                t2 = await s2.get_attribute('title')
                p2 = await s2.get_attribute('data-price')
                
                print(f"Testing click on swatch 1 ({t1}: {p1})...")
                await s1.click()
                await page.wait_for_timeout(500)
                card_p1 = await card.locator('[ref="priceContainer"], product-price, .price').first.text_content()
                print(f"Card price after swatch 1: {card_p1.strip()}")

                print(f"Testing click on swatch 2 ({t2}: {p2})...")
                await s2.click()
                await page.wait_for_timeout(500)
                card_p2 = await card.locator('[ref="priceContainer"], product-price, .price').first.text_content()
                print(f"Card price after swatch 2: {card_p2.strip()}")

                await card.screenshot(path=os.path.join(out_dir, "verified_carey_card_swatches.png"))
                print("Captured verified_carey_card_swatches.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
