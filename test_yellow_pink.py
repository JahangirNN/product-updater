import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    print("Testing live variant price update with Gold/Soft Yellow (15499) vs Gold/Pink (26599)...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        
        await page.goto("https://therareavenue.com/products/teri-shoulder-bag", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

        initial_price = await page.locator('product-price').first.text_content()
        print(f"Initial price text: {initial_price.strip()}", flush=True)

        # 1. Click Gold/Soft Yellow (should be Rs. 15,499)
        yellow_inp = page.locator('variant-picker input[value="Gold/Soft Yellow"]').first
        if await yellow_inp.count() > 0:
            print("Clicking Gold/Soft Yellow...", flush=True)
            parent = yellow_inp.locator('xpath=..')
            await parent.click()
            await page.wait_for_timeout(3000)
            yellow_price = await page.locator('product-price').first.text_content()
            print(f"Price after Gold/Soft Yellow: {yellow_price.strip()} (Expected: Rs. 15,499)", flush=True)
            print(f"Current page URL: {page.url}", flush=True)
            await page.screenshot(path=os.path.join(out_dir, "variant_yellow_test.png"))

        # 2. Click Gold/Pink (should be Rs. 26,599)
        pink_inp = page.locator('variant-picker input[value="Gold/Pink"]').first
        if await pink_inp.count() > 0:
            print("Clicking Gold/Pink...", flush=True)
            parent = pink_inp.locator('xpath=..')
            await parent.click()
            await page.wait_for_timeout(3000)
            pink_price = await page.locator('product-price').first.text_content()
            print(f"Price after Gold/Pink: {pink_price.strip()} (Expected: Rs. 26,599)", flush=True)
            print(f"Current page URL: {page.url}", flush=True)
            await page.screenshot(path=os.path.join(out_dir, "variant_pink_test.png"))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
