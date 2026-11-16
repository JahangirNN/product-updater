import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    print("Testing live variant price update with Gold/Pink (26,599) vs default (20,899)...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        
        await page.goto("https://therareavenue.com/products/teri-shoulder-bag", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

        initial_price = await page.locator('product-price').first.text_content()
        print(f"Initial price text: {initial_price.strip()} (Expected: Rs. 20,899)", flush=True)

        # Click Gold/Pink
        pink_inp = page.locator('variant-picker input[value="Gold/Pink"]').first
        parent = pink_inp.locator('xpath=..')
        print("Clicking Gold/Pink...", flush=True)
        await parent.click(force=True)
        await page.wait_for_timeout(3000)

        pink_price = await page.locator('product-price').first.text_content()
        print(f"Price after Gold/Pink: {pink_price.strip()} (Expected: Rs. 26,599)", flush=True)
        print(f"Current page URL: {page.url}", flush=True)
        await page.screenshot(path=os.path.join(out_dir, "variant_pink_price_result.png"))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
