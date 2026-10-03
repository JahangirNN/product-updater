import asyncio
import os
from playwright.async_api import async_playwright

BRAIN_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(BRAIN_DIR, exist_ok=True)

STORE_URL = "https://therareavenue.com"

async def test_live_navigation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop Tests
        print("=" * 70)
        print("1. RUNNING DESKTOP NAVIGATION TESTS (1440x900)")
        print("=" * 70)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(STORE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Hover over Men
        print("\n[Desktop] Hovering over 'Men'...")
        men_trigger = page.locator('.luxury-nav__trigger[data-title="Men"]')
        await men_trigger.hover()
        await asyncio.sleep(1)

        men_menu = page.locator('details:has(summary[data-title="Men"]) .luxury-mega-menu')

        # Verify Men Coach Footwear Link
        men_coach_fw = men_menu.locator('a:has-text("COACH Footwear")').first
        men_coach_href = await men_coach_fw.get_attribute("href")
        print(f"  Men -> COACH Footwear href: {men_coach_href}")
        assert "/collections/coach/men+footwear" in men_coach_href, f"Unexpected Men Coach FW href: {men_coach_href}"

        # Verify Men MK Footwear Link
        men_mk_fw = men_menu.locator('a:has-text("Michael Kors Footwear")').first
        men_mk_href = await men_mk_fw.get_attribute("href")
        print(f"  Men -> Michael Kors Footwear href: {men_mk_href}")
        assert "/collections/michael-kors/men+footwear" in men_mk_href, f"Unexpected Men MK FW href: {men_mk_href}"

        # Click Men COACH Footwear
        print("  Navigating to Men COACH Footwear via click...")
        await men_coach_fw.click()
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)
        shot_men_coach = os.path.join(BRAIN_DIR, "verified_men_coach_footwear_pdp_grid.png")
        await page.screenshot(path=shot_men_coach)
        print(f"  Saved screenshot: {shot_men_coach}")
        print(f"  Page URL: {page.url}")

        # Hover over Women
        print("\n[Desktop] Hovering over 'Women'...")
        women_trigger = page.locator('.luxury-nav__trigger[data-title="Women"]')
        await women_trigger.hover()
        await asyncio.sleep(1)

        women_menu = page.locator('details:has(summary[data-title="Women"]) .luxury-mega-menu')

        women_coach_fw = women_menu.locator('a:has-text("COACH Footwear")').first
        women_coach_href = await women_coach_fw.get_attribute("href")
        print(f"  Women -> COACH Footwear href: {women_coach_href}")
        assert "/collections/coach/women+footwear" in women_coach_href, f"Unexpected Women Coach FW href: {women_coach_href}"

        women_mk_fw = women_menu.locator('a:has-text("Michael Kors Footwear")').first
        women_mk_href = await women_mk_fw.get_attribute("href")
        print(f"  Women -> Michael Kors Footwear href: {women_mk_href}")
        assert "/collections/michael-kors/women+footwear" in women_mk_href, f"Unexpected Women MK FW href: {women_mk_href}"

        # Click Women COACH Footwear
        print("  Navigating to Women COACH Footwear via click...")
        await women_coach_fw.click()
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)
        shot_women_coach = os.path.join(BRAIN_DIR, "verified_women_coach_footwear_pdp_grid.png")
        await page.screenshot(path=shot_women_coach)
        print(f"  Saved screenshot: {shot_women_coach}")
        print(f"  Page URL: {page.url}")

        await page.close()

        # 2. Mobile Drawer Tests
        print("\n" + "=" * 70)
        print("2. RUNNING MOBILE NAVIGATION TESTS (390x844)")
        print("=" * 70)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15"
        )
        mob_page = await context.new_page()
        await mob_page.goto(STORE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Open sidebar menu
        menu_btn = mob_page.locator('button[aria-controls="sidebar-menu"]')
        await menu_btn.click()
        await asyncio.sleep(1)

        # Open Men panel
        print("  Opening Men panel in mobile drawer...")
        men_btn = mob_page.locator('button[aria-controls="header-panel-men"]')
        await men_btn.click()
        await asyncio.sleep(1)

        # Find Coach Footwear inside Men panel
        mob_men_coach = mob_page.locator('#header-panel-men a:has-text("COACH Footwear")')
        mob_men_coach_href = await mob_men_coach.get_attribute("href")
        print(f"  Mobile Men -> COACH Footwear href: {mob_men_coach_href}")
        assert "/collections/coach/men+footwear" in mob_men_coach_href

        # Find MK Footwear inside Men panel
        mob_men_mk = mob_page.locator('#header-panel-men a:has-text("Michael Kors Footwear")')
        mob_men_mk_href = await mob_men_mk.get_attribute("href")
        print(f"  Mobile Men -> Michael Kors Footwear href: {mob_men_mk_href}")
        assert "/collections/michael-kors/men+footwear" in mob_men_mk_href

        shot_mob_men = os.path.join(BRAIN_DIR, "verified_mobile_drawer_men_footwear.png")
        await mob_page.screenshot(path=shot_mob_men)
        print(f"  Saved mobile screenshot: {shot_mob_men}")

        # Close Men panel and open Women panel
        back_btn = mob_page.locator('#header-panel-men button[data-action="close-panel"]')
        await back_btn.click()
        await asyncio.sleep(0.5)

        print("  Opening Women panel in mobile drawer...")
        women_btn = mob_page.locator('button[aria-controls="header-panel-women"]')
        await women_btn.click()
        await asyncio.sleep(1)

        mob_women_coach = mob_page.locator('#header-panel-women a:has-text("COACH Footwear")')
        mob_women_coach_href = await mob_women_coach.get_attribute("href")
        print(f"  Mobile Women -> COACH Footwear href: {mob_women_coach_href}")
        assert "/collections/coach/women+footwear" in mob_women_coach_href

        shot_mob_women = os.path.join(BRAIN_DIR, "verified_mobile_drawer_women_footwear.png")
        await mob_page.screenshot(path=shot_mob_women)
        print(f"  Saved mobile screenshot: {shot_mob_women}")

        await mob_page.close()
        await browser.close()
        print("\nALL LIVE NAVIGATION VERIFICATION TESTS PASSED SUCCESSFULLY!")

asyncio.run(test_live_navigation())
