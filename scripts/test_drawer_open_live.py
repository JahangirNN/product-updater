"""
Verify drawer open interaction on iPad Mini portrait and landscape.
"""
import asyncio
import os
import sys
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_drawer_open():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        for name, w, h in [("ipad_mini_portrait_768", 768, 1024), ("ipad_mini_landscape_1024", 1024, 768)]:
            ctx = await browser.new_context(
                viewport={"width": w, "height": h},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True
            )
            page = await ctx.new_page()
            await page.goto("https://therareavenue.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)

            # Click the hamburger menu button
            drawer_btn = page.locator(".header__icon--summary, summary[aria-label='Menu']").first
            await drawer_btn.click()
            await page.wait_for_timeout(1000)

            # Check if drawer opened
            is_open = await page.evaluate("""() => {
                const details = document.querySelector('#Details-menu-drawer-container');
                return details ? details.hasAttribute('open') : false;
            }""")

            shot_path = os.path.join(ARTIFACT_DIR, f"live_{name}_drawer_opened.png")
            await page.screenshot(path=shot_path)
            print(f"[{name}] Drawer opened: {is_open}, saved to {shot_path}")

            await ctx.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_drawer_open())
