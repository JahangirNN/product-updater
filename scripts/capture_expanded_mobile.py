import asyncio
import os
from playwright.async_api import async_playwright

BRAIN_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
STORE_URL = "https://therareavenue.com"

async def capture_open_mobile_accordions():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()
        await page.goto(STORE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Open sidebar
        menu_btn = page.locator('button[aria-controls="sidebar-menu"]')
        await menu_btn.click()
        await asyncio.sleep(1)

        # Open Men panel
        men_btn = page.locator('button[aria-controls="header-panel-men"]')
        await men_btn.click()
        await asyncio.sleep(1)

        # Expand Premium Footwear accordion
        fw_acc = page.locator('#header-panel-men summary:has-text("Premium Footwear")')
        await fw_acc.click()
        await asyncio.sleep(0.5)

        shot_mob_men_fw = os.path.join(BRAIN_DIR, "verified_mobile_drawer_men_footwear_expanded.png")
        await page.screenshot(path=shot_mob_men_fw)
        print(f"Saved expanded Men mobile screenshot: {shot_mob_men_fw}")

        # Go back to main
        back_btn = page.locator('#header-panel-men button[data-action="close-panel"]')
        await back_btn.click()
        await asyncio.sleep(0.5)

        # Open Women panel
        women_btn = page.locator('button[aria-controls="header-panel-women"]')
        await women_btn.click()
        await asyncio.sleep(1)

        # Expand Luxury Footwear accordion
        fw_w_acc = page.locator('#header-panel-women summary:has-text("Luxury Footwear")')
        await fw_w_acc.click()
        await asyncio.sleep(0.5)

        shot_mob_women_fw = os.path.join(BRAIN_DIR, "verified_mobile_drawer_women_footwear_expanded.png")
        await page.screenshot(path=shot_mob_women_fw)
        print(f"Saved expanded Women mobile screenshot: {shot_mob_women_fw}")

        await page.close()
        await browser.close()

asyncio.run(capture_open_mobile_accordions())
