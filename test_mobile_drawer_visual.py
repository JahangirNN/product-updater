import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def run():
    print("Starting Playwright...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 393, "height": 852},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        print("Navigating to https://therareavenue.com...", flush=True)
        try:
            await page.goto("https://therareavenue.com", wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"Warning during goto: {e}", flush=True)
            
        await page.wait_for_timeout(3000)
        
        out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"
        await page.screenshot(path=os.path.join(out_dir, "mobile_home_initial.png"))
        print("Captured mobile_home_initial.png", flush=True)

        # Let's inspect the hamburger button in header
        # In Horizon theme: <header-drawer> -> <details id="Details-menu-drawer-container"> -> <summary class="header__icon--menu">
        # Or look for SVG with hamburger
        summary = page.locator('header-drawer summary, .header__icon--menu, summary[aria-label="Menu"], [aria-controls="menu-drawer"]').first
        if await summary.count() > 0:
            print("Clicking hamburger summary...", flush=True)
            await summary.click()
        else:
            print("Trying generic header details/summary...", flush=True)
            await page.locator('header details summary').first.click()

        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(out_dir, "mobile_drawer_current.png"))
        print("Captured mobile_drawer_current.png", flush=True)

        await browser.close()
        print("Done!", flush=True)

if __name__ == "__main__":
    asyncio.run(run())
