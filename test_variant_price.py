import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    print("Testing live variant price update on Teri Shoulder Bag...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        
        await page.goto("https://therareavenue.com/products/teri-shoulder-bag", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

        # Check initial price text
        initial_price = await page.locator('product-price').first.text_content()
        print(f"Initial price text: {initial_price.strip()}", flush=True)
        await page.screenshot(path=os.path.join(out_dir, "variant_test_initial.png"))

        # Look for swatch or input for Gold/Soft Yellow or Gold/Pink
        inputs = await page.locator('variant-picker input[type="radio"]').all()
        print(f"Found {len(inputs)} variant inputs", flush=True)

        for i, inp in enumerate(inputs[:10]):
            val = await inp.get_attribute("value")
            checked = await inp.is_checked()
            print(f"Input {i}: val={val}, checked={checked}")

        # Let's find an input that is not checked and click it
        for inp in inputs:
            val = await inp.get_attribute("value")
            checked = await inp.is_checked()
            if not checked and val:
                print(f"Clicking variant input: {val}...", flush=True)
                parent_label = inp.locator('xpath=..')
                await parent_label.click()
                await page.wait_for_timeout(3000)
                new_price = await page.locator('product-price').first.text_content()
                print(f"New price text after clicking {val}: {new_price.strip()}", flush=True)
                await page.screenshot(path=os.path.join(out_dir, f"variant_test_clicked_{val.replace('/', '_')}.png"))
                break

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
