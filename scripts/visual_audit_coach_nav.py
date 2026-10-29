import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()

        print("1. Opening homepage...")
        await page.goto("https://therareavenue.com", wait_until="domcontentloaded")
        
        # Hover over Men
        print("2. Hovering over MEN...")
        men_nav = page.locator("a.header__linklist-link:has-text('Men'), button:has-text('Men')").first
        await men_nav.hover()
        await page.wait_for_timeout(1000)
        
        # Find Coach Footwear link
        coach_fw_link = page.locator("a:has-text('COACH Footwear')").first
        if await coach_fw_link.is_visible():
            href = await coach_fw_link.get_attribute("href")
            print(f"COACH Footwear link href: {href}")
            
            # Click it
            print("3. Clicking COACH Footwear link...")
            await coach_fw_link.click()
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            
            print(f"Current URL: {page.url}")
            await page.screenshot(path="C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/men_coach_footwear_click.png", full_page=False)
            
            # Extract product titles visible on page
            titles = await page.locator(".product-card__title, .product-item__title, a.bold").all_inner_texts()
            print(f"Visible product titles ({len(titles)}):")
            for t in titles[:10]:
                print(f" - {t}")
        else:
            print("COACH Footwear link not visible on hover!")

        await browser.close()

asyncio.run(run())
