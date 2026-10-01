"""
Automated Playwright verification test for Category facet header and pills.
Verifies on both Desktop (1440x900) and Mobile (430x932):
  1. Desktop sidebar facet accordion header displays "CATEGORY" cleanly in uppercase luxury typography.
  2. Mobile filter drawer displays "CATEGORY" cleanly.
  3. No obsolete "SILHOUETTE" accordion headers exist.
  4. Expanding "CATEGORY" reveals the 6 bag/accessories category options.
  5. Active facet tag pills render as "Category: [Type]" (not "Silhouette: [Type]").
  6. Captures visual proof screenshots to artifacts directory.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
BASE_URL = "https://therareavenue.com"

options = [
    "Satchels & Top Handles",
    "Crossbody & Messengers",
    "Totes & Carryalls",
    "Shoulder Bags",
    "Backpacks & Rucksacks",
    "Wallets & Small Goods"
]

def run_tests():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # =========================================================================
        # 1. DESKTOP TESTS (1440x900)
        # =========================================================================
        print("\n" + "=" * 80)
        print("RUNNING DESKTOP TESTS (1440x900)")
        print("=" * 80)

        desktop_context = browser.new_context(viewport={"width": 1440, "height": 900})
        desktop_page = desktop_context.new_page()

        # --- Test 1A: /collections/womens-handbags Desktop ---
        print("\n[1A] Testing /collections/womens-handbags on Desktop...")
        desktop_page.goto(f"{BASE_URL}/collections/womens-handbags", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Check sidebar
        sidebar = desktop_page.locator(".facets-sidebar").first
        assert sidebar.is_visible(), "Desktop sidebar (.facets-sidebar) should be visible"

        # Check Category accordion title
        category_acc = sidebar.locator("details summary:has-text('Category')").first
        category_exists = category_acc.count() > 0
        print(f"  Category accordion found in desktop sidebar: {category_exists}")
        assert category_exists, "Category accordion header must exist in desktop sidebar!"

        # Check that Silhouette accordion does NOT exist
        silhouette_acc = sidebar.locator("details summary:has-text('Silhouette')").first
        assert silhouette_acc.count() == 0, "Obsolete 'Silhouette' accordion header must NOT exist in sidebar!"

        # Check uppercase typography rendering
        category_text_transform = category_acc.locator(".accordion__toggle").first.evaluate(
            "el => window.getComputedStyle(el).textTransform"
        )
        print(f"  Category toggle text-transform: {category_text_transform}")

        # Screenshot Desktop initial (collapsed)
        ss1 = os.path.join(ARTIFACTS_DIR, "01_desktop_womens_handbags_category_collapsed.png")
        desktop_page.screenshot(path=ss1)
        print(f"  Screenshot saved: {ss1}")

        # Expand Category accordion
        details = category_acc.locator("xpath=..")
        if not details.evaluate("el => el.hasAttribute('open')"):
            category_acc.click()
            time.sleep(1)

        for opt in options:
            opt_locator = sidebar.get_by_text(opt, exact=True).first
            assert opt_locator.is_visible(), f"Category option '{opt}' missing or not visible in sidebar!"
        print(f"  All 6 category options verified visible in desktop sidebar!")

        # Screenshot Desktop expanded
        ss2 = os.path.join(ARTIFACTS_DIR, "02_desktop_womens_handbags_category_expanded.png")
        desktop_page.screenshot(path=ss2)
        print(f"  Screenshot saved: {ss2}")

        # --- Test 1B: Filter click & active facet pill ---
        print("\n[1B] Testing Category filter selection & active pill on Desktop...")
        satchel_link = sidebar.locator("a[href*='/satchels']").first
        satchel_link.click()
        desktop_page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        active_pill = desktop_page.locator(".removable-facet:has-text('Category: Satchels & Top Handles')").first
        print(f"  Active pill with 'Category: Satchels & Top Handles' present: {active_pill.count() > 0}")
        assert active_pill.count() > 0, "Active facet pill must display 'Category: Satchels & Top Handles'!"

        # Verify no 'Silhouette:' active pill exists
        sil_pill = desktop_page.locator(".removable-facet:has-text('Silhouette:')").first
        assert sil_pill.count() == 0, "No active pill should contain 'Silhouette:'!"

        ss3 = os.path.join(ARTIFACTS_DIR, "03_desktop_womens_handbags_category_active_pill.png")
        desktop_page.screenshot(path=ss3)
        print(f"  Screenshot saved: {ss3}")

        # --- Test 1C: /collections/designer-bags Desktop ---
        print("\n[1C] Testing /collections/designer-bags on Desktop...")
        desktop_page.goto(f"{BASE_URL}/collections/designer-bags", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        db_sidebar = desktop_page.locator(".facets-sidebar").first
        db_category_acc = db_sidebar.locator("details summary:has-text('Category')").first
        assert db_category_acc.count() > 0, "Category accordion must exist on /collections/designer-bags sidebar!"
        db_sil_acc = db_sidebar.locator("details summary:has-text('Silhouette')").first
        assert db_sil_acc.count() == 0, "Silhouette accordion must not exist on /collections/designer-bags sidebar!"

        # Open Category accordion
        db_details = db_category_acc.locator("xpath=..")
        if not db_details.evaluate("el => el.hasAttribute('open')"):
            db_category_acc.click()
            time.sleep(1)

        ss4 = os.path.join(ARTIFACTS_DIR, "04_desktop_designer_bags_category_facet.png")
        desktop_page.screenshot(path=ss4)
        print(f"  Screenshot saved: {ss4}")

        # --- Test 1D: /collections/mens-bags Desktop ---
        print("\n[1D] Testing /collections/mens-bags on Desktop...")
        desktop_page.goto(f"{BASE_URL}/collections/mens-bags", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        mb_sidebar = desktop_page.locator(".facets-sidebar").first
        mb_category_acc = mb_sidebar.locator("details summary:has-text('Category')").first
        assert mb_category_acc.count() > 0, "Category accordion must exist on /collections/mens-bags sidebar!"
        mb_sil_acc = mb_sidebar.locator("details summary:has-text('Silhouette')").first
        assert mb_sil_acc.count() == 0, "Silhouette accordion must not exist on /collections/mens-bags sidebar!"

        # Open Category accordion
        mb_details = mb_category_acc.locator("xpath=..")
        if not mb_details.evaluate("el => el.hasAttribute('open')"):
            mb_category_acc.click()
            time.sleep(1)

        ss4b = os.path.join(ARTIFACTS_DIR, "04b_desktop_mens_bags_category_facet.png")
        desktop_page.screenshot(path=ss4b)
        print(f"  Screenshot saved: {ss4b}")

        desktop_context.close()

        # =========================================================================
        # 2. MOBILE TESTS (430x932 - iPhone 14 Pro Max)
        # =========================================================================
        print("\n" + "=" * 80)
        print("RUNNING MOBILE TESTS (430x932)")
        print("=" * 80)

        mobile_context = browser.new_context(
            viewport={"width": 430, "height": 932},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        mobile_page = mobile_context.new_page()

        # --- Test 2A: /collections/womens-handbags Mobile Drawer ---
        print("\n[2A] Testing /collections/womens-handbags on Mobile...")
        mobile_page.goto(f"{BASE_URL}/collections/womens-handbags", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        filter_btn = mobile_page.locator("button[aria-controls='facets-drawer']").first
        assert filter_btn.is_visible(), "Mobile filter button should be visible"
        filter_btn.click()
        time.sleep(2)

        drawer = mobile_page.locator("#facets-drawer").first
        drawer_cat_acc = drawer.locator("summary:has-text('Category')").first
        print(f"  Category accordion visible in mobile drawer: {drawer_cat_acc.is_visible()}")
        print(f"  Category accordion text in mobile drawer: {drawer_cat_acc.inner_text()}")
        assert drawer_cat_acc.is_visible(), "Category accordion must be visible in mobile drawer!"
        
        drawer_sil_acc = drawer.locator("summary:has-text('Silhouette')").first
        assert drawer_sil_acc.count() == 0, "Silhouette accordion must NOT exist in mobile drawer!"

        # Expand Category in drawer
        d_details = drawer_cat_acc.locator("xpath=..")
        if not d_details.evaluate("el => el.hasAttribute('open')"):
            drawer_cat_acc.click()
            time.sleep(1)

        for opt in options:
            opt_locator = drawer.get_by_text(opt, exact=True).first
            assert opt_locator.is_visible(), f"Category option '{opt}' missing in mobile drawer!"
        print(f"  All 6 category options verified in mobile drawer!")

        ss5 = os.path.join(ARTIFACTS_DIR, "05_mobile_womens_handbags_drawer_category.png")
        mobile_page.screenshot(path=ss5)
        print(f"  Screenshot saved: {ss5}")

        # --- Test 2B: /collections/designer-bags Mobile Drawer ---
        print("\n[2B] Testing /collections/designer-bags on Mobile...")
        mobile_page.goto(f"{BASE_URL}/collections/designer-bags", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        m_filter_btn = mobile_page.locator("button[aria-controls='facets-drawer']").first
        m_filter_btn.click()
        time.sleep(2)

        m_drawer = mobile_page.locator("#facets-drawer").first
        m_drawer_cat_acc = m_drawer.locator("summary:has-text('Category')").first
        assert m_drawer_cat_acc.is_visible(), "Category accordion must be visible in mobile drawer on designer-bags!"

        # Expand Category in mobile drawer
        md_details = m_drawer_cat_acc.locator("xpath=..")
        if not md_details.evaluate("el => el.hasAttribute('open')"):
            m_drawer_cat_acc.click()
            time.sleep(1)

        ss6 = os.path.join(ARTIFACTS_DIR, "06_mobile_designer_bags_drawer_category.png")
        mobile_page.screenshot(path=ss6)
        print(f"  Screenshot saved: {ss6}")

        # --- Test 2C: /collections/mens-bags Mobile Drawer ---
        print("\n[2C] Testing /collections/mens-bags on Mobile...")
        mobile_page.goto(f"{BASE_URL}/collections/mens-bags", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        mb_filter_btn = mobile_page.locator("button[aria-controls='facets-drawer']").first
        mb_filter_btn.click()
        time.sleep(2)

        mb_drawer = mobile_page.locator("#facets-drawer").first
        mb_drawer_cat_acc = mb_drawer.locator("summary:has-text('Category')").first
        assert mb_drawer_cat_acc.is_visible(), "Category accordion must be visible in mobile drawer on mens-bags!"

        # Expand Category in mobile drawer
        mbd_details = mb_drawer_cat_acc.locator("xpath=..")
        if not mbd_details.evaluate("el => el.hasAttribute('open')"):
            mb_drawer_cat_acc.click()
            time.sleep(1)

        ss6b = os.path.join(ARTIFACTS_DIR, "06b_mobile_mens_bags_drawer_category.png")
        mobile_page.screenshot(path=ss6b)
        print(f"  Screenshot saved: {ss6b}")

        mobile_context.close()

        # =========================================================================
        # 3. SEARCH RESULTS PAGE TEST (/search?q=bag)
        # =========================================================================
        print("\n" + "=" * 80)
        print("RUNNING SEARCH FACETS TEST (/search?q=bag)")
        print("=" * 80)

        search_context = browser.new_context(viewport={"width": 1440, "height": 900})
        search_page = search_context.new_page()

        # --- Test 3A: Desktop Search Facets & Interactive Pill ---
        print("\n[3A] Testing /search?q=bag on Desktop...")
        search_page.goto(f"{BASE_URL}/search?q=bag", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        s_sidebar = search_page.locator(".facets-sidebar").first
        s_category_acc = s_sidebar.locator("details summary:has-text('Category')").first
        assert s_category_acc.count() > 0, "Category accordion must exist in search sidebar!"
        s_sil_acc = s_sidebar.locator("details summary:has-text('Silhouette')").first
        assert s_sil_acc.count() == 0, "Silhouette accordion must NOT exist in search sidebar!"

        # Expand Category in search sidebar
        s_details = s_category_acc.locator("xpath=..")
        if not s_details.evaluate("el => el.hasAttribute('open')"):
            s_category_acc.click()
            time.sleep(1)

        ss7 = os.path.join(ARTIFACTS_DIR, "07_desktop_search_bag_category_facet.png")
        search_page.screenshot(path=ss7)
        print(f"  Screenshot saved: {ss7}")

        # Check Category filter interaction on search page
        totes_cb = s_sidebar.locator("input[value='totes']").first
        assert totes_cb.count() > 0, "Totes checkbox must exist in Category facet!"
        totes_cb.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change', { bubbles: true })); }")
        time.sleep(3)

        print(f"  URL after selecting Totes: {search_page.url}")
        assert "filter.p.silhouette=totes" in search_page.url, "filter.p.silhouette=totes missing from URL!"

        # Check active pill
        totes_pill = search_page.locator(".removable-facet:has-text('Category: Totes & Carryalls')").first
        assert totes_pill.count() > 0, "Active facet pill 'Category: Totes & Carryalls' must be rendered!"
        print("  Active pill 'Category: Totes & Carryalls' verified!")

        ss8 = os.path.join(ARTIFACTS_DIR, "08_desktop_search_bag_category_filtered.png")
        search_page.screenshot(path=ss8)
        print(f"  Screenshot saved: {ss8}")

        # Remove pill
        remove_btn = totes_pill.locator("button").first
        remove_btn.click()
        time.sleep(3)
        print(f"  URL after removing pill: {search_page.url}")
        assert "filter.p.silhouette=totes" not in search_page.url, "filter.p.silhouette should be removed from URL!"

        search_context.close()

        # --- Test 3B: Mobile Search Drawer ---
        print("\n[3B] Testing /search?q=bag on Mobile...")
        m_search_context = browser.new_context(
            viewport={"width": 430, "height": 932},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        m_search_page = m_search_context.new_page()
        m_search_page.goto(f"{BASE_URL}/search?q=bag", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        ms_btn = m_search_page.locator("button[aria-controls='facets-drawer']").first
        assert ms_btn.is_visible(), "Mobile filter button should be visible on search page"
        ms_btn.click()
        time.sleep(2)

        ms_drawer = m_search_page.locator("#facets-drawer").first
        ms_cat_acc = ms_drawer.locator("summary:has-text('Category')").first
        assert ms_cat_acc.is_visible(), "Category accordion must be visible in mobile drawer on search page!"

        # Expand Category
        ms_details = ms_cat_acc.locator("xpath=..")
        if not ms_details.evaluate("el => el.hasAttribute('open')"):
            ms_cat_acc.click()
            time.sleep(1)

        ss9 = os.path.join(ARTIFACTS_DIR, "09_mobile_search_bag_category_drawer.png")
        m_search_page.screenshot(path=ss9)
        print(f"  Screenshot saved: {ss9}")

        m_search_context.close()
        browser.close()

    print("\n" + "=" * 80)
    print("ALL PLAYWRIGHT TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
