import asyncio
import os
import re
from playwright.async_api import async_playwright

async def run():
    print("Testing Mobile Navigation Flow with exact text matching...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 393, "height": 852},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        
        import time
        url = f"https://therareavenue.com?v={int(time.time())}"
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2500)

        out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

        # Open drawer
        summary = page.locator('header-drawer summary, .header__icon--menu, summary[aria-label="Menu"]').first
        await summary.click()
        await page.wait_for_timeout(1000)

        # 1. Click Men with exact match
        men_header = page.locator('.luxury-lvl1-header').filter(has=page.locator('.luxury-lvl1-title', has_text=re.compile(r"^Men$", re.IGNORECASE))).first
        if await men_header.count() > 0:
            print("Clicking Level 1 Men...", flush=True)
            await men_header.click()
            await page.wait_for_timeout(600)
            await page.screenshot(path=os.path.join(out_dir, "nav_step_men_expanded.png"))
            print("Captured nav_step_men_expanded.png", flush=True)
            
            # Click Level 2 Men's Footwear inside Men
            men_shoes = page.locator('.luxury-lvl2-header', has_text="Premium Footwear & Sneakers").first
            if await men_shoes.count() > 0:
                print("Clicking Men's Footwear...", flush=True)
                await men_shoes.click()
                await page.wait_for_timeout(600)
                await page.screenshot(path=os.path.join(out_dir, "nav_step_men_shoes_expanded.png"))
                print("Captured nav_step_men_shoes_expanded.png", flush=True)

        # 2. Click Designers & Maisons
        brands_header = page.locator('.luxury-lvl1-header', has_text="Designers & Maisons").first
        if await brands_header.count() > 0:
            print("Clicking Level 1 Designers & Maisons...", flush=True)
            await brands_header.click()
            await page.wait_for_timeout(600)
            await page.screenshot(path=os.path.join(out_dir, "nav_step_designers_expanded.png"))
            print("Captured nav_step_designers_expanded.png", flush=True)

            # Click Swiss & Luxury Horology inside Designers
            horology = page.locator('.luxury-lvl2-header', has_text="Swiss & Luxury Horology").first
            if await horology.count() > 0:
                print("Clicking Swiss Horology...", flush=True)
                await horology.click()
                await page.wait_for_timeout(600)
                await page.screenshot(path=os.path.join(out_dir, "nav_step_designers_horology_expanded.png"))
                print("Captured nav_step_designers_horology_expanded.png", flush=True)

        await browser.close()
        print("Done testing all departments!", flush=True)

if __name__ == "__main__":
    asyncio.run(run())
