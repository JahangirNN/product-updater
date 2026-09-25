import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()

        print("1. Loading home page...")
        await page.goto("https://therareavenue.com", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)

        # Hover over Women
        women_btn = page.locator("summary[data-title='Women']").first
        await women_btn.hover()
        await asyncio.sleep(1)

        # Find Citizen link in mega menu
        citizen_link = page.locator("a[href*='/collections/citizen']").first
        citizen_href = await citizen_link.get_attribute("href")
        print(f"Citizen link href in Women's mega menu: {citizen_href}")

        # Click Citizen link
        print("2. Navigating to Citizen showroom via mega-menu link...")
        await citizen_link.click()
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)
        print(f"Current URL: {page.url}")

        page_title = await page.locator("h1").first.text_content()
        print(f"Page H1: {page_title.strip() if page_title else 'None'}")

        # Capture Citizen collection screenshot
        await page.screenshot(path="C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/citizen_showroom_verified.png")

        # Now check /collections/womens-watches description
        print("3. Checking womens-watches collection description...")
        await page.goto("https://therareavenue.com/collections/womens-watches", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)

        body_text = await page.inner_text("body")
        has_old_text = "from Versace and Tissot" in body_text
        print(f"Contains old text 'from Versace and Tissot'? {has_old_text}")
        has_new_desc = "blending luxury jewelry craftsmanship" in body_text or "Swiss and Japanese" in body_text or "precision" in body_text
        print(f"Contains modern text? {has_new_desc}")

        await page.screenshot(path="C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/womens_watches_clean_verified.png")

        await browser.close()
        print("Verification complete!")

if __name__ == "__main__":
    asyncio.run(run())
