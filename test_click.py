import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 393, "height": 852},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        await page.goto("https://therareavenue.com", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Open drawer
        summary = page.locator('header-drawer summary, .header__icon--menu, summary[aria-label="Menu"]').first
        await summary.click()
        await page.wait_for_timeout(1000)

        out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

        # Try clicking bottom WOMEN (+)
        dept_item = page.locator('.luxury-sidebar-nav .dept-header').first
        await dept_item.click()
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(out_dir, "mobile_drawer_bottom_women_clicked.png"))
        print("Captured mobile_drawer_bottom_women_clicked.png", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
