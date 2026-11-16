import asyncio
import os
import time
from playwright.async_api import async_playwright

async def run():
    print("Testing PLP card with Noor Top Handle Bag (different prices per color)...", flush=True)
    out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        
        url = f"https://therareavenue.com/search?q=noor+top+handle+bag&v={int(time.time())}"
        print(f"Navigating to {url}...", flush=True)
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2500)

        card = page.locator('product-card, .product-card').first
        if await card.count() > 0:
            swatches = await card.locator('.luxury-card__color-btn').all()
            print(f"Found {len(swatches)} swatches on Noor card:")
            for i, s in enumerate(swatches):
                title = await s.get_attribute('title')
                price = await s.get_attribute('data-price')
                print(f"  [{i}] Swatch: {title} | Price: {price}")

            # Click Swatch 0 (Brown Canvas: 13,599)
            await swatches[0].click()
            await page.wait_for_timeout(400)
            p0 = await card.locator('[ref="priceContainer"], product-price, .price').first.text_content()
            print(f"Card price after Swatch 0: {p0.strip()} (Expected: Rs. 13,599)")

            # Click Swatch 2 (White Croc: 14,699)
            if len(swatches) > 2:
                await swatches[2].click()
                await page.wait_for_timeout(400)
                p2 = await card.locator('[ref="priceContainer"], product-price, .price').first.text_content()
                print(f"Card price after Swatch 2 (White Croc): {p2.strip()} (Expected: Rs. 14,699)")

            # Click Swatch 3 (Deep Burgundy: 12,499)
            if len(swatches) > 3:
                await swatches[3].click()
                await page.wait_for_timeout(400)
                p3 = await card.locator('[ref="priceContainer"], product-price, .price').first.text_content()
                print(f"Card price after Swatch 3 (Deep Burgundy): {p3.strip()} (Expected: Rs. 12,499)")

            await card.screenshot(path=os.path.join(out_dir, "verified_noor_card_diff_prices.png"))
            print("Captured verified_noor_card_diff_prices.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
