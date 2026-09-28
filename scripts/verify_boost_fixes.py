import asyncio
import os
import sys

from playwright.async_api import async_playwright

ARTIFACTS_DIR = "C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

async def run_visual_verification():
    print("=" * 80)
    print("RUNNING PLAYWRIGHT VISUAL VERIFICATION FOR BOOST FIXES")
    print(f"Artifacts output directory: {ARTIFACTS_DIR}")
    print("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ---------------------------------------------------------------------
        # 1. Desktop Verification: Collection Header Dark Typography
        # ---------------------------------------------------------------------
        d_context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await d_context.new_page()

        print("\n[1/5] Checking /collections/womens-handbags header typography...")
        await page.goto("https://therareavenue.com/collections/womens-handbags", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Verify title exists and check computed color
        h1 = page.locator("h1.h1").first
        if await h1.count() > 0:
            color = await h1.evaluate("el => window.getComputedStyle(el).color")
            title_text = await h1.inner_text()
            print(f"  Title: '{title_text}', Computed Color: {color}")
        else:
            print("  WARNING: h1.h1 not found")

        # Capture header screenshot
        banner = page.locator(".shopify-section--collection-banner").first
        if await banner.count() > 0:
            await banner.screenshot(path=os.path.join(ARTIFACTS_DIR, "womens_handbags_header_after.png"))
            print("  Saved womens_handbags_header_after.png")
        else:
            await page.screenshot(path=os.path.join(ARTIFACTS_DIR, "womens_handbags_header_after.png"))

        print("\n[2/5] Checking /collections/mens-bags header typography...")
        await page.goto("https://therareavenue.com/collections/mens-bags", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        h1_m = page.locator("h1.h1").first
        if await h1_m.count() > 0:
            color_m = await h1_m.evaluate("el => window.getComputedStyle(el).color")
            title_m = await h1_m.inner_text()
            print(f"  Title: '{title_m}', Computed Color: {color_m}")

        banner_m = page.locator(".shopify-section--collection-banner").first
        if await banner_m.count() > 0:
            await banner_m.screenshot(path=os.path.join(ARTIFACTS_DIR, "mens_bags_header_after.png"))
            print("  Saved mens_bags_header_after.png")

        # ---------------------------------------------------------------------
        # 2. Facet Filter Indicators and Michael Kors Brand Normalization
        # ---------------------------------------------------------------------
        print("\n[3/5] Checking Facet Filter Checkboxes and Brand Normalization on /collections/womens-handbags...")
        await page.goto("https://therareavenue.com/collections/womens-handbags", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Check for luxury-facet-checkbox presence
        checkboxes = page.locator(".luxury-facet-checkbox")
        cb_count = await checkboxes.count()
        print(f"  Found {cb_count} .luxury-facet-checkbox indicator rings on page")

        # Check vendor label "Michael Kors" vs "MICHAEL Michael Kors"
        mk_raw_count = await page.get_by_text("MICHAEL Michael Kors", exact=True).count()
        mk_clean_count = await page.locator(".facets").get_by_text("Michael Kors", exact=True).count()
        print(f"  Unnormalized 'MICHAEL Michael Kors' occurrences in facets: {mk_raw_count}")
        print(f"  Clean 'Michael Kors' occurrences in facets: {mk_clean_count}")

        # Capture facets sidebar
        facets_sidebar = page.locator(".facets-sidebar").first
        if await facets_sidebar.count() > 0 and await facets_sidebar.is_visible():
            await facets_sidebar.screenshot(path=os.path.join(ARTIFACTS_DIR, "facet_filter_sidebar_after.png"))
            print("  Saved facet_filter_sidebar_after.png")
        else:
            await page.screenshot(path=os.path.join(ARTIFACTS_DIR, "facet_filter_sidebar_after.png"))
            print("  Saved full page facet_filter_sidebar_after.png")

        # Test active state on satchels filter
        print("  Navigating to /collections/womens-handbags/satchels to verify active indicator state...")
        await page.goto("https://therareavenue.com/collections/womens-handbags/satchels", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        active_cb = page.locator(".luxury-facet-checkbox--active")
        active_count = await active_cb.count()
        print(f"  Active checkbox rings found: {active_count}")
        await page.screenshot(path=os.path.join(ARTIFACTS_DIR, "facet_filter_active_satchels.png"))
        print("  Saved facet_filter_active_satchels.png")

        # ---------------------------------------------------------------------
        # 3. Desktop Mega-Menu Promo Card Hyphenation
        # ---------------------------------------------------------------------
        print("\n[4/5] Checking Desktop Mega-Menu Promo Card Hyphenation...")
        await page.goto("https://therareavenue.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        women_btn = page.locator('summary.luxury-nav__trigger[data-title="Women"]')
        if await women_btn.count() > 0:
            await women_btn.first.hover()
            await page.wait_for_timeout(1000)

            promo_body = page.locator(".luxury-mega-menu__promo-body").first
            if await promo_body.count() > 0:
                body_text = await promo_body.inner_text()
                computed_hyphens = await promo_body.evaluate("el => window.getComputedStyle(el).hyphens")
                print(f"  Promo Body Text: '{body_text}'")
                print(f"  Computed hyphens property: '{computed_hyphens}'")

            promo_card = page.locator(".luxury-mega-menu__promo").first
            if await promo_card.count() > 0 and await promo_card.is_visible():
                await promo_card.screenshot(path=os.path.join(ARTIFACTS_DIR, "desktop_promo_card_after.png"), timeout=5000)
                print("  Saved desktop_promo_card_after.png")
            else:
                await page.screenshot(path=os.path.join(ARTIFACTS_DIR, "desktop_promo_card_after.png"))
                print("  Saved desktop_promo_card_after.png via page screenshot")

        # ---------------------------------------------------------------------
        # 4. Mobile Drawer Brands Scroller Safe-Area Padding
        # ---------------------------------------------------------------------
        print("\n[5/5] Checking Mobile Drawer Brands Panel Safe-Area Bottom Padding...")
        m_context = await browser.new_context(viewport={"width": 390, "height": 844})
        m_page = await m_context.new_page()
        await m_page.goto("https://therareavenue.com", wait_until="domcontentloaded")
        await m_page.wait_for_timeout(2000)

        # Open sidebar drawer
        hamburger = m_page.locator('button[aria-controls="sidebar-menu"]').first
        if await hamburger.count() > 0:
            await hamburger.click()
            await m_page.wait_for_timeout(1000)

            # Click Brands button in sidebar
            brands_panel_btn = m_page.locator('button[aria-controls="header-panel-brands"]').first
            if await brands_panel_btn.count() > 0:
                await brands_panel_btn.click()
                await m_page.wait_for_timeout(1000)

                # Scroll down in the brands panel list
                brands_panel = m_page.locator("#header-panel-brands .header-sidebar__linklist").first
                if await brands_panel.count() > 0:
                    padding_bottom = await brands_panel.evaluate("el => window.getComputedStyle(el).paddingBottom")
                    print(f"  Brands panel computed padding-bottom: {padding_bottom}")

                    # Scroll to bottom to view Versace / Movado
                    await brands_panel.evaluate("el => el.parentElement.scrollTop = el.parentElement.scrollHeight")
                    await m_page.wait_for_timeout(1000)

                await m_page.screenshot(path=os.path.join(ARTIFACTS_DIR, "mobile_drawer_brands_bottom_after.png"))
                print("  Saved mobile_drawer_brands_bottom_after.png")
            else:
                print("  Brands panel button not found by aria-controls")
                await m_page.screenshot(path=os.path.join(ARTIFACTS_DIR, "mobile_drawer_brands_bottom_after.png"))

        print("\n" + "=" * 80)
        print("PLAYWRIGHT VISUAL VERIFICATION COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_visual_verification())
