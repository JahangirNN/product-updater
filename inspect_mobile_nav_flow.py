import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def run():
    print("Starting Playwright Mobile Inspection Flow...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 393, "height": 852},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        
        # Add timestamp to avoid caching
        import time
        url = f"https://therareavenue.com?v={int(time.time())}"
        print(f"Navigating to {url}...", flush=True)
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

        # 1. Open mobile drawer
        summary = page.locator('header-drawer summary, .header__icon--menu, summary[aria-label="Menu"]').first
        await summary.click()
        await page.wait_for_timeout(1000)

        # Step 1: Initial Drawer View (No Women/Men/Brands repeated!)
        step1_path = os.path.join(out_dir, "nav_step1_drawer_initial.png")
        await page.screenshot(path=step1_path)
        print(f"Captured {step1_path}", flush=True)

        # Step 2: Click Level 1 "Women"
        women_header = page.locator('.luxury-lvl1-header', has_text="Women").first
        if await women_header.count() > 0:
            print("Clicking Level 1 Women...", flush=True)
            await women_header.click()
            await page.wait_for_timeout(600) # Wait for 300ms CSS grid transition
            step2_path = os.path.join(out_dir, "nav_step2_women_expanded.png")
            await page.screenshot(path=step2_path)
            print(f"Captured {step2_path}", flush=True)
        else:
            print("Women header not found!", flush=True)

        # Step 3: Click Level 2 "Designer Handbags" inside Women
        bags_header = page.locator('.luxury-lvl2-header', has_text="Designer Handbags").first
        if await bags_header.count() > 0:
            print("Clicking Level 2 Designer Handbags...", flush=True)
            await bags_header.click()
            await page.wait_for_timeout(600) # Wait for transition
            step3_path = os.path.join(out_dir, "nav_step3_bags_expanded.png")
            await page.screenshot(path=step3_path)
            print(f"Captured {step3_path}", flush=True)
        else:
            print("Designer Handbags header not found!", flush=True)

        # Step 4: Click Level 2 "Luxury Watches" inside Women (should expand watches, collapse bags)
        watches_header = page.locator('.luxury-lvl2-header', has_text="Luxury Watches").first
        if await watches_header.count() > 0:
            print("Clicking Level 2 Luxury Watches...", flush=True)
            await watches_header.click()
            await page.wait_for_timeout(600)
            step4_path = os.path.join(out_dir, "nav_step4_watches_expanded.png")
            await page.screenshot(path=step4_path)
            print(f"Captured {step4_path}", flush=True)

        # Step 5: Click Level 1 "Men" (should close Women, expand Men)
        men_header = page.locator('.luxury-lvl1-header', has_text="Men").first
        if await men_header.count() > 0:
            print("Clicking Level 1 Men...", flush=True)
            await men_header.click()
            await page.wait_for_timeout(600)
            step5_path = os.path.join(out_dir, "nav_step5_men_expanded.png")
            await page.screenshot(path=step5_path)
            print(f"Captured {step5_path}", flush=True)

        await browser.close()
        print("Inspection flow complete!", flush=True)

if __name__ == "__main__":
    asyncio.run(run())
