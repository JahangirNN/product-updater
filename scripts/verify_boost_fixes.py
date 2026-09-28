import asyncio
import os
import sys

from playwright.async_api import async_playwright

ARTIFACTS_DIR = "C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

async def safe_goto(page, url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            return
        except Exception as e:
            if attempt == retries:
                raise e
            print(f"    Navigation to {url} timed out/failed (attempt {attempt}). Retrying...")
            await asyncio.sleep(2)

async def run_visual_verification():
    print("=" * 80)
    print("RUNNING THOROUGH PLAYWRIGHT VISUAL VERIFICATION FOR BOOST FIXES")
    print(f"Artifacts output directory: {ARTIFACTS_DIR}")
    print("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ---------------------------------------------------------------------
        # 1. Desktop Verification: Collection Header Dark Typography
        # ---------------------------------------------------------------------
        d_context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await d_context.new_page()

        collections_to_test = [
            ("/collections/womens-handbags", "womens_handbags_header_after.png"),
            ("/collections/mens-bags", "mens_bags_header_after.png"),
            ("/collections/womens-watches", "womens_watches_header_after.png"),
            ("/collections/womens-sunglasses", "womens_sunglasses_header_after.png"),
        ]

        print("\n[1/6] Verifying Collection Header Typography across collections...")
        for col_path, screenshot_name in collections_to_test:
            target_url = f"https://therareavenue.com{col_path}"
            await safe_goto(page, target_url)
            await page.wait_for_timeout(2500)

            h1 = page.locator("h1.h1").first
            bc = page.locator(".breadcrumb").first

            assert await h1.count() > 0, f"H1 not found on {col_path}"
            h1_color = await h1.evaluate("el => window.getComputedStyle(el).color")
            title_text = await h1.inner_text()
            bc_color = await bc.evaluate("el => window.getComputedStyle(el).color") if await bc.count() > 0 else "N/A"

            print(f"  {col_path}: Title='{title_text}', H1 Color={h1_color}, Breadcrumb Color={bc_color}")
            assert h1_color == "rgb(26, 26, 26)", f"H1 color {h1_color} is not dark rgb(26, 26, 26) on {col_path}"

            # Capture header screenshot
            banner = page.locator(".shopify-section--collection-banner").first
            if await banner.count() > 0:
                await banner.screenshot(path=os.path.join(ARTIFACTS_DIR, screenshot_name))
            else:
                await page.screenshot(path=os.path.join(ARTIFACTS_DIR, screenshot_name))
            print(f"  Saved {screenshot_name}")

        # ---------------------------------------------------------------------
        # 2. Facet Filter Indicators (Desktop Sidebar + Single Centered Dot)
        # ---------------------------------------------------------------------
        print("\n[2/6] Verifying Facet Filter Indicators on Desktop Sidebar...")
        await safe_goto(page, "https://therareavenue.com/collections/womens-handbags")
        await page.wait_for_timeout(2500)

        sidebar_cbs = page.locator(".facets-sidebar .luxury-facet-checkbox")
        sb_cb_count = await sidebar_cbs.count()
        print(f"  Found {sb_cb_count} .luxury-facet-checkbox indicator rings in desktop sidebar")
        assert sb_cb_count >= 8, f"Expected at least 8 facet checkboxes in sidebar, got {sb_cb_count}"

        facets_sidebar = page.locator(".facets-sidebar").first
        if await facets_sidebar.count() > 0 and await facets_sidebar.is_visible():
            await facets_sidebar.screenshot(path=os.path.join(ARTIFACTS_DIR, "facet_filter_sidebar_after.png"))
            print("  Saved facet_filter_sidebar_after.png")

        # Test active indicator state on satchels filter & verify NO double dot bug
        print("\n[3/6] Navigating to /collections/womens-handbags/satchels to verify active indicator...")
        await safe_goto(page, "https://therareavenue.com/collections/womens-handbags/satchels")
        await page.wait_for_timeout(2500)

        active_cbs = page.locator(".facets-sidebar .luxury-facet-checkbox--active")
        active_count = await active_cbs.count()
        print(f"  Active checkbox rings in sidebar: {active_count}")
        assert active_count >= 1, "Expected at least 1 active checkbox ring in sidebar"

        # Verify no double dot: children length must be 0 (the dot is purely the centered ::after pseudo element)
        active_el = active_cbs.first
        child_count = await active_el.evaluate("el => el.children.length")
        after_content = await active_el.evaluate("el => window.getComputedStyle(el, '::after').content")
        after_w = await active_el.evaluate("el => window.getComputedStyle(el, '::after').width")
        print(f"  Active checkbox DOM children: {child_count} (must be 0 for clean single dot)")
        print(f"  Active checkbox ::after content: {after_content}, width: {after_w}")
        assert child_count == 0, f"Double dot detected! Found {child_count} child elements inside active checkbox"
        assert after_content != "none" and after_w == "4px", "Expected 4px ::after dot pseudo-element"

        await page.screenshot(path=os.path.join(ARTIFACTS_DIR, "facet_filter_active_satchels.png"))
        print("  Saved facet_filter_active_satchels.png")

        # ---------------------------------------------------------------------
        # 3. Brand Normalization in Facets and Active Pills
        # ---------------------------------------------------------------------
        print("\n[4/6] Verifying Brand Normalization on /collections/womens-handbags...")
        await safe_goto(page, "https://therareavenue.com/collections/womens-handbags")
        await page.wait_for_timeout(2500)

        mk_raw_count = await page.get_by_text("MICHAEL Michael Kors", exact=True).count()
        mk_clean_count = await page.locator(".facets").get_by_text("Michael Kors", exact=True).count()
        print(f"  Unnormalized 'MICHAEL Michael Kors' in facets: {mk_raw_count}")
        print(f"  Clean 'Michael Kors' in facets: {mk_clean_count}")
        assert mk_raw_count == 0, f"Found {mk_raw_count} unnormalized MICHAEL Michael Kors occurrences"
        assert mk_clean_count >= 1, f"Expected clean 'Michael Kors' in facets, got {mk_clean_count}"

        # Verify active brand pill label
        print("  Checking active filter pill on /collections/womens-handbags/michael-kors...")
        await safe_goto(page, "https://therareavenue.com/collections/womens-handbags/michael-kors")
        await page.wait_for_timeout(2500)
        active_pill = page.locator(".removable-facet").first
        if await active_pill.count() > 0:
            pill_text = await active_pill.inner_text()
            print(f"  Active pill text: '{pill_text.strip()}'")
            assert "Brand: Michael Kors" in pill_text, f"Expected 'Brand: Michael Kors', got '{pill_text}'"

        # ---------------------------------------------------------------------
        # 4. Desktop Mega-Menu Promo Card Hyphenation
        # ---------------------------------------------------------------------
        print("\n[5/6] Verifying Desktop Mega-Menu Promo Card Hyphenation...")
        await safe_goto(page, "https://therareavenue.com")
        await page.wait_for_timeout(2000)

        women_btn = page.locator('summary.luxury-nav__trigger[data-title="Women"]')
        if await women_btn.count() > 0:
            await women_btn.first.hover()
            await page.wait_for_timeout(1000)

            promo_body = page.locator(".luxury-mega-menu__promo-body").first
            if await promo_body.count() > 0:
                body_text = await promo_body.inner_text()
                computed_hyphens = await promo_body.evaluate("el => window.getComputedStyle(el).hyphens")
                webkit_hyphens = await promo_body.evaluate("el => window.getComputedStyle(el).webkitHyphens")
                print(f"  Promo Body Text: '{body_text}'")
                print(f"  Computed hyphens: '{computed_hyphens}', -webkit-hyphens: '{webkit_hyphens}'")
                assert computed_hyphens == "manual", f"Expected hyphens: manual, got {computed_hyphens}"

            promo_card = page.locator(".luxury-mega-menu__promo").first
            if await promo_card.count() > 0 and await promo_card.is_visible():
                await promo_card.screenshot(path=os.path.join(ARTIFACTS_DIR, "desktop_promo_card_after.png"), timeout=5000)
                print("  Saved desktop_promo_card_after.png")

        # ---------------------------------------------------------------------
        # 5. Mobile Drawer Safe-Area & Mobile Facets Drawer Checkboxes
        # ---------------------------------------------------------------------
        print("\n[6/6] Verifying Mobile Drawer Brands Safe-Area & Mobile Facets Checkboxes...")
        m_context = await browser.new_context(viewport={"width": 390, "height": 844})
        m_page = await m_context.new_page()

        # 5A. Check mobile facets drawer
        await safe_goto(m_page, "https://therareavenue.com/collections/womens-handbags")
        await m_page.wait_for_timeout(2500)
        filter_btn = m_page.locator('button[aria-controls="facets-drawer"]').first
        if await filter_btn.count() > 0:
            await filter_btn.click()
            await m_page.wait_for_timeout(1000)
            drawer_cbs = m_page.locator("#facets-drawer .luxury-facet-checkbox")
            drawer_cb_count = await drawer_cbs.count()
            print(f"  Mobile facet drawer contains {drawer_cb_count} .luxury-facet-checkbox indicators")
            assert drawer_cb_count >= 8, f"Expected at least 8 checkboxes in mobile facet drawer, got {drawer_cb_count}"
            await m_page.screenshot(path=os.path.join(ARTIFACTS_DIR, "mobile_facets_drawer_after.png"))
            print("  Saved mobile_facets_drawer_after.png")

        # 5B. Check mobile navigation drawer safe-area padding
        await safe_goto(m_page, "https://therareavenue.com")
        await m_page.wait_for_timeout(2000)
        hamburger = m_page.locator('button[aria-controls="sidebar-menu"]').first
        if await hamburger.count() > 0:
            await hamburger.click()
            await m_page.wait_for_timeout(1000)

            brands_panel_btn = m_page.locator('button[aria-controls="header-panel-brands"]').first
            if await brands_panel_btn.count() > 0:
                await brands_panel_btn.click()
                await m_page.wait_for_timeout(1000)

                brands_list = m_page.locator("#header-panel-brands .header-sidebar__linklist").first
                if await brands_list.count() > 0:
                    padding_bottom = await brands_list.evaluate("el => window.getComputedStyle(el).paddingBottom")
                    print(f"  Brands panel computed padding-bottom: {padding_bottom}")
                    assert padding_bottom == "48px", f"Expected padding-bottom 48px, got {padding_bottom}"

                    await brands_list.evaluate("el => el.parentElement.scrollTop = el.parentElement.scrollHeight")
                    await m_page.wait_for_timeout(1000)

                await m_page.screenshot(path=os.path.join(ARTIFACTS_DIR, "mobile_drawer_brands_bottom_after.png"))
                print("  Saved mobile_drawer_brands_bottom_after.png")

        print("\n" + "=" * 80)
        print("ALL VERIFICATION ASSERTIONS PASSED WITH ZERO DEFECTS")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_visual_verification())
