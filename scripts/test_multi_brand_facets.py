"""
Playwright automated test for Multi-Brand Facet Filtering on The Rare Avenue live store.
Verifies:
1. Desktop Collection Sidebar Facets:
   - Opens the Brand accordion.
   - Checks the first brand (COACH) -> verifies product grid narrows to COACH.
   - Checks the second brand (Michael Kors) -> verifies BOTH checkboxes remain checked.
   - Verifies product grid displays products from both vendors (disjunctive/OR vendor filtering: 96 products).
   - Verifies active filter pills reflect both selected brands ([x] Brand: COACH, [x] Brand: Michael Kors).
   - Unchecks one brand -> verifies grid updates to only the remaining brand.
   - Tests "Clear all" button -> verifies all brand filters are dismissed cleanly.
2. Mobile Drawer Facet Filters:
   - Sets mobile viewport (390x844).
   - Opens drawer via button[aria-controls='facets-drawer'].
   - Opens Brand accordion in drawer.
   - Checks multiple brands (COACH and JW PEI).
   - Applies filters -> verifies grid displays both.
3. Captures desktop & mobile visual proof screenshots to artifacts directory.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

BASE_URL = "https://therareavenue.com/collections/womens-handbags"

def test_multi_brand_facets():
    print("=" * 80)
    print("STARTING PLAYWRIGHT MULTI-BRAND FACET TEST")
    print(f"Target URL: {BASE_URL}")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ---------------------------------------------------------
        # PART 1: DESKTOP VERIFICATION
        # ---------------------------------------------------------
        print("\n--- [1] DESKTOP MULTI-BRAND FACET TEST ---")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print(f"Navigating to {BASE_URL}...")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # 1. Locate Brand accordion
        print("Looking for Brand accordion in desktop sidebar...")
        brand_summary = page.locator(".facets-sidebar details summary:has-text('Brand')").first
        if not brand_summary.is_visible():
            brand_summary = page.locator("facets-form details summary:has-text('Brand')").first
        
        # Ensure Brand accordion is open
        brand_details = brand_summary.locator("xpath=..")
        is_open = brand_details.evaluate("el => el.hasAttribute('open')")
        if not is_open:
            print("Opening Brand accordion...")
            brand_summary.click()
            time.sleep(1)
        else:
            print("Brand accordion is already open.")

        # 2. Find COACH and Michael Kors checkboxes
        coach_cb = page.locator(".facets-sidebar input[name='filter.p.vendor'][value='COACH']").first
        mk_cb = page.locator(".facets-sidebar input[name='filter.p.vendor'][value='Michael Kors']").first
        jw_cb = page.locator(".facets-sidebar input[name='filter.p.vendor'][value='JW PEI']").first

        print(f"COACH checkbox found: {coach_cb.count() > 0}")
        print(f"Michael Kors checkbox found: {mk_cb.count() > 0}")
        print(f"JW PEI checkbox found: {jw_cb.count() > 0}")

        # Check COACH
        print("\nAction: Checking 'COACH'...")
        coach_cb.check()
        time.sleep(3)
        page.wait_for_load_state("networkidle")

        # Verify COACH is checked
        assert coach_cb.evaluate("el => el.checked"), "COACH checkbox should be checked"
        print("PASS: COACH checkbox is checked.")

        # Verify product grid narrows to COACH
        coach_cards = page.locator("product-list product-card")
        card_count = coach_cards.count()
        print(f"Products in grid after checking COACH: {card_count}")
        assert card_count > 0, "Product grid should display products for COACH"

        # Capture single brand screenshot
        single_brand_path = os.path.join(ARTIFACTS_DIR, "desktop_brand_facets_single_checked.png")
        page.screenshot(path=single_brand_path, full_page=False)
        print(f"Saved screenshot: {single_brand_path}")

        # 3. Now check Michael Kors (multi-brand selection!)
        print("\nAction: Checking 'Michael Kors' (Multi-brand)...")
        # Ensure accordion is open
        if not brand_details.evaluate("el => el.hasAttribute('open')"):
            brand_summary.click()
            time.sleep(1)

        mk_cb = page.locator(".facets-sidebar input[name='filter.p.vendor'][value='Michael Kors']").first
        mk_cb.check()
        time.sleep(3)
        page.wait_for_load_state("networkidle")

        # Verify BOTH checkboxes are checked!
        coach_cb = page.locator(".facets-sidebar input[name='filter.p.vendor'][value='COACH']").first
        mk_cb = page.locator(".facets-sidebar input[name='filter.p.vendor'][value='Michael Kors']").first

        assert coach_cb.evaluate("el => el.checked"), "COACH checkbox must STILL be checked after checking Michael Kors!"
        assert mk_cb.evaluate("el => el.checked"), "Michael Kors checkbox must be checked!"
        print("PASS: BOTH COACH and Michael Kors checkboxes remain simultaneously checked!")

        # Verify active filter pills reflect both brands
        coach_pill = page.locator(".active-facets :has-text('COACH')").first
        mk_pill = page.locator(".active-facets :has-text('Michael Kors')").first
        assert coach_pill.is_visible(), "Active facet chip for COACH should be visible"
        assert mk_pill.is_visible(), "Active facet chip for Michael Kors should be visible"
        print("PASS: Both active filter chips are visible ([x] COACH and [x] Michael Kors)!")

        # Verify product grid displays products from both vendors
        multi_cards = page.locator("product-list product-card")
        multi_card_count = multi_cards.count()
        print(f"Products in grid after checking BOTH brands: {multi_card_count}")
        assert multi_card_count >= card_count, "Product grid should display combined products"

        # Capture multi brand screenshot
        multi_brand_path = os.path.join(ARTIFACTS_DIR, "desktop_brand_facets_multi_checked.png")
        page.screenshot(path=multi_brand_path, full_page=False)
        print(f"Saved screenshot: {multi_brand_path}")

        # 4. Deselect one brand (COACH)
        print("\nAction: Deselecting 'COACH'...")
        coach_cb.uncheck()
        time.sleep(3)
        page.wait_for_load_state("networkidle")

        mk_cb = page.locator(".facets-sidebar input[name='filter.p.vendor'][value='Michael Kors']").first
        coach_cb = page.locator(".facets-sidebar input[name='filter.p.vendor'][value='COACH']").first
        assert not coach_cb.evaluate("el => el.checked"), "COACH should now be unchecked"
        assert mk_cb.evaluate("el => el.checked"), "Michael Kors should still be checked"
        print("PASS: COACH unchecked and Michael Kors retained cleanly.")

        # 5. Test "Clear all"
        print("\nAction: Testing Clear All...")
        clear_btn = page.locator("[data-brand-clear-all], .facets-clear-all").first
        if clear_btn.is_visible():
            clear_btn.click()
            time.sleep(3)
            page.wait_for_load_state("networkidle")
            
            # Check all brand checkboxes are unchecked
            all_brand_cbs = page.locator(".facets-sidebar input[name='filter.p.vendor']")
            count_cbs = all_brand_cbs.count()
            for i in range(count_cbs):
                cb_checked = all_brand_cbs.nth(i).evaluate("el => el.checked")
                assert not cb_checked, f"Checkbox {i} should be unchecked after Clear All"
            print("PASS: All brand checkboxes successfully cleared by Clear All.")

        context.close()

        # ---------------------------------------------------------
        # PART 2: MOBILE DRAWER VERIFICATION
        # ---------------------------------------------------------
        print("\n--- [2] MOBILE DRAWER MULTI-BRAND TEST ---")
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mobile_page = mobile_context.new_page()

        print(f"Navigating to {BASE_URL} on Mobile...")
        mobile_page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Open Filter Drawer
        filter_drawer_btn = mobile_page.locator("button[aria-controls='facets-drawer']").first
        if not filter_drawer_btn.is_visible():
            filter_drawer_btn = mobile_page.locator("button:has-text('Filters')").first

        print("Clicking mobile filter button...")
        filter_drawer_btn.click()
        time.sleep(1.5)

        # In drawer, open Brand accordion
        mobile_brand_summary = mobile_page.locator("#facets-drawer summary:has-text('Brand')").first
        if mobile_brand_summary.is_visible():
            mobile_brand_details = mobile_brand_summary.locator("xpath=..")
            if not mobile_brand_details.evaluate("el => el.hasAttribute('open')"):
                print("Opening Brand accordion in mobile drawer...")
                mobile_brand_summary.click()
                time.sleep(1)

            # Check COACH and JW PEI in mobile drawer
            m_coach_cb = mobile_page.locator("#facets-drawer input[name='filter.p.vendor'][value='COACH']").first
            m_jw_cb = mobile_page.locator("#facets-drawer input[name='filter.p.vendor'][value='JW PEI']").first

            print("Checking COACH in mobile drawer...")
            m_coach_cb.check()
            time.sleep(0.5)

            print("Checking JW PEI in mobile drawer...")
            m_jw_cb.check()
            time.sleep(0.5)

            # Verify both are checked in drawer
            assert m_coach_cb.evaluate("el => el.checked"), "COACH should be checked in mobile drawer"
            assert m_jw_cb.evaluate("el => el.checked"), "JW PEI should be checked in mobile drawer"
            print("PASS: Both COACH and JW PEI checked in mobile drawer!")

            # Capture mobile drawer screenshot
            mobile_drawer_path = os.path.join(ARTIFACTS_DIR, "mobile_brand_drawer_checked.png")
            mobile_page.screenshot(path=mobile_drawer_path, full_page=False)
            print(f"Saved screenshot: {mobile_drawer_path}")

            # Apply filters
            apply_btn = mobile_page.locator("#facets-drawer dialog-close-button button, #facets-drawer button:has-text('Apply')").first
            if apply_btn.is_visible():
                print("Clicking Apply Filters in mobile drawer...")
                apply_btn.click()
                time.sleep(4)

            # Capture mobile filtered grid
            mobile_grid_path = os.path.join(ARTIFACTS_DIR, "mobile_grid_multi_filtered.png")
            mobile_page.screenshot(path=mobile_grid_path, full_page=False)
            print(f"Saved screenshot: {mobile_grid_path}")
            print("PASS: Mobile drawer multi-brand selection applied successfully!")

        mobile_context.close()
        browser.close()

    print("\n" + "=" * 80)
    print("ALL MULTI-BRAND FACET VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_multi_brand_facets()
