import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_drawer_on_ipad():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        for w, h, name in [(768, 1024, "ipad_mini_portrait_768"), (1024, 768, "ipad_mini_landscape_1024")]:
            context = await browser.new_context(
                viewport={"width": w, "height": h},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()
            await page.goto("https://therareavenue.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # Screenshot initial header
            s1 = os.path.join(SCREENSHOT_DIR, f"diag_{name}_initial.png")
            await page.screenshot(path=s1)
            print(f"Captured: {s1}")

            # Try to open hamburger menu
            hamburger = page.locator(".header__icon--menu, summary[aria-label*='Menu'], .header__drawer summary").first
            count = await hamburger.count()
            print(f"{name}: Hamburger found: {count}")

            if count > 0:
                await hamburger.click()
                await page.wait_for_timeout(1000)
                s2 = os.path.join(SCREENSHOT_DIR, f"diag_{name}_drawer_opened.png")
                await page.screenshot(path=s2)
                print(f"Captured: {s2}")

            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_drawer_on_ipad())
