import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        
        print("Navigating to https://therareavenue.com/collections/coach/women+footwear ...")
        await page.goto("https://therareavenue.com/collections/coach/women+footwear", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        shot_path = "C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/visual_coach_women_footwear.png"
        await page.screenshot(path=shot_path, full_page=False)
        print(f"Saved screenshot: {shot_path}")

        print("Navigating to https://therareavenue.com/collections/michael-kors/women+footwear ...")
        await page.goto("https://therareavenue.com/collections/michael-kors/women+footwear", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        shot_path_mk = "C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/visual_mk_women_footwear.png"
        await page.screenshot(path=shot_path_mk, full_page=False)
        print(f"Saved screenshot: {shot_path_mk}")

        await browser.close()

asyncio.run(run())
