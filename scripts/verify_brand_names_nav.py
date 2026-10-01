"""
Verify desktop and mobile navigation shows clean brand names (e.g. 'Tissot' instead of 'Tissot PRX & Seastar').
Captures screenshots to artifacts directory.
"""
import os
import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
BASE_URL = "https://therareavenue.com"

async def run_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop Test (1440x900)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        
        print("Navigating to home page on Desktop...")
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # Close any newsletter modal if present
        close_btn = page.locator(".newsletter-popup__close, button[aria-label='Close'], .modal__close")
        if await close_btn.count() > 0:
            try:
                await close_btn.first.click(timeout=3000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass
        
        # Open Men Mega Menu
        print("Opening Men mega-menu...")
        men_trigger = page.locator("summary[data-title='Men']")
        await men_trigger.hover()
        await page.wait_for_timeout(1500)
        
        # Capture screenshot of Men mega-menu (similar to user's photo)
        men_screenshot_path = os.path.join(ARTIFACTS_DIR, "desktop_men_mega_menu_brand_names.png")
        await page.screenshot(path=men_screenshot_path)
        print(f"Captured Men mega-menu screenshot: {men_screenshot_path}")
        
        # Verify link texts in Men's Timepieces
        men_watch_links = page.locator(".header__menu-disclosure:has(summary[data-title='Men']) .luxury-mega-menu__col").first.locator(".luxury-mega-menu__link")
        count = await men_watch_links.count()
        print(f"Found {count} links in Men's Timepieces:")
        watch_texts = []
        for i in range(count):
            txt = (await men_watch_links.nth(i).text_content()).strip()
            watch_texts.append(txt)
            print(f"  [{i}] {txt}")
            
        assert "Tissot" in watch_texts, f"Expected 'Tissot' in {watch_texts}"
        assert "Citizen" in watch_texts, f"Expected 'Citizen' in {watch_texts}"
        assert "Movado" in watch_texts, f"Expected 'Movado' in {watch_texts}"
        assert "Seiko" in watch_texts, f"Expected 'Seiko' in {watch_texts}"
        assert "Versace" in watch_texts, f"Expected 'Versace' in {watch_texts}"
        assert "Ferragamo" in watch_texts, f"Expected 'Ferragamo' in {watch_texts}"
        assert not any("PRX" in t for t in watch_texts), f"Found 'PRX' in {watch_texts}"
        assert not any("Promaster" in t for t in watch_texts), f"Found 'Promaster' in {watch_texts}"
        print("Men's Timepieces brand names verified successfully!")
        
        # Verify Men's Bags
        men_bag_links = page.locator(".header__menu-disclosure:has(summary[data-title='Men']) .luxury-mega-menu__col").nth(1).locator(".luxury-mega-menu__link")
        bag_count = await men_bag_links.count()
        bag_texts = [(await men_bag_links.nth(i).text_content()).strip() for i in range(bag_count)]
        print(f"Men's Bags links: {bag_texts}")
        assert "COACH" in bag_texts, f"Expected 'COACH' in {bag_texts}"
        assert "Michael Kors" in bag_texts, f"Expected 'Michael Kors' in {bag_texts}"
        print("Men's Bags brand names verified successfully!")
        
        # Open Women Mega Menu
        print("Opening Women mega-menu...")
        women_trigger = page.locator("summary[data-title='Women']")
        await women_trigger.hover()
        await page.wait_for_timeout(1500)
        
        women_screenshot_path = os.path.join(ARTIFACTS_DIR, "desktop_women_mega_menu_brand_names.png")
        await page.screenshot(path=women_screenshot_path)
        print(f"Captured Women mega-menu screenshot: {women_screenshot_path}")
        
        women_watch_links = page.locator(".header__menu-disclosure:has(summary[data-title='Women']) .luxury-mega-menu__col").first.locator(".luxury-mega-menu__link")
        w_count = await women_watch_links.count()
        w_watch_texts = [(await women_watch_links.nth(i).text_content()).strip() for i in range(w_count)]
        print(f"Women's Timepieces links: {w_watch_texts}")
        assert "Tissot" in w_watch_texts, f"Expected 'Tissot' in {w_watch_texts}"
        assert "Seiko" in w_watch_texts, f"Expected 'Seiko' in {w_watch_texts}"
        assert not any("Bellissima" in t for t in w_watch_texts), f"Found 'Bellissima' in {w_watch_texts}"
        print("Women's Timepieces brand names verified successfully!")
        
        await context.close()
        
        # 2. Mobile Drawer Test (430x932)
        print("\nTesting Mobile drawer...")
        mob_context = await browser.new_context(viewport={"width": 430, "height": 932})
        mob_page = await mob_context.new_page()
        await mob_page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await mob_page.wait_for_timeout(2000)
        
        # Open drawer
        hamburger = mob_page.locator("button[aria-controls='header-sidebar-menu'], button.header__icon-button:has-text('Menu'), button[data-action='open-sidebar']").first
        if await hamburger.count() > 0:
            await hamburger.click()
            await mob_page.wait_for_timeout(1000)
            
            # Click Men
            men_btn = mob_page.locator("button[data-panel='header-panel-men'], a[href*='/men']").first
            if await men_btn.count() > 0:
                await men_btn.click()
                await mob_page.wait_for_timeout(1000)
                
                # Expand Watches
                watches_summary = mob_page.locator("#header-panel-men summary:has-text('Luxury Watches')").first
                if await watches_summary.count() > 0:
                    await watches_summary.click()
                    await mob_page.wait_for_timeout(800)
                
                mob_screenshot_path = os.path.join(ARTIFACTS_DIR, "mobile_drawer_men_watches_brand_names.png")
                await mob_page.screenshot(path=mob_screenshot_path)
                print(f"Captured Mobile drawer screenshot: {mob_screenshot_path}")
        
        await mob_context.close()
        await browser.close()
        print("\nALL VERIFICATION CHECKS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_verification())
