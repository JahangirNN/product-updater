import asyncio
import os
from playwright.async_api import async_playwright

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJECT_ROOT, "artifacts", "header_responsive_test")
os.makedirs(OUT_DIR, exist_ok=True)

STORE_URL = "https://therareavenue.com"

async def test_viewports():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 800})
        
        loaded = False
        for attempt in range(1, 4):
            try:
                print(f"Loading page (attempt {attempt})...", flush=True)
                await page.goto(STORE_URL, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(2)
                loaded = True
                break
            except Exception as e:
                print(f"Attempt {attempt} failed: {e}", flush=True)
                await asyncio.sleep(3)
                
        if not loaded:
            print("Failed to load page.", flush=True)
            await browser.close()
            return
            
        viewports = [1000, 1050, 1100, 1150, 1200, 1280, 1440]
        for w in viewports:
            await page.set_viewport_size({"width": w, "height": 800})
            await asyncio.sleep(1)
            
            nav = page.locator('.header__primary-nav')
            logo = page.locator('.header__logo')
            
            nav_box = await nav.bounding_box()
            logo_box = await logo.bounding_box()
            
            shot_path = os.path.join(OUT_DIR, f"header_{w}px.png")
            await page.screenshot(path=shot_path)
            
            if nav_box and logo_box:
                nav_right = nav_box['x'] + nav_box['width']
                logo_left = logo_box['x']
                gap = logo_left - nav_right
                print(f"Viewport {w}px: Nav right={nav_right:.1f}, Logo left={logo_left:.1f}, GAP={gap:.1f}px", flush=True)
            else:
                print(f"Viewport {w}px: elements not found", flush=True)
                
        await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_viewports())
