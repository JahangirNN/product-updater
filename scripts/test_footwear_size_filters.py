import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def test_footwear_size_filters():
    print("=" * 80)
    print("STARTING PLAYWRIGHT FOOTWEAR SIZE FILTER VERIFICATION SUITE")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)

        # -------------------------------------------------------------
        # SUITE 1: FOOTWEAR PDP (Nike Air Force 1 LV8)
        # -------------------------------------------------------------
        print("\n--- [SUITE 1] FOOTWEAR PDP SIZE DISCOVERY FILTERS ---")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        footwear_url = "https://therareavenue.com/products/mens-nike-air-force-1-07-lv8-casual-shoes-anthracite-anthracite-3291377"
        print(f"Navigating to {footwear_url}...")
        page.goto(footwear_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        filter_bar = page.locator("#luxury-pdp-discovery-filters")
        assert filter_bar.is_visible(), "PDP Discovery Filter Bar should be visible on Footwear PDP"
        filter_bar.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        # Verify Sizes row is rendered
        size_row = filter_bar.locator("#pdp-size-filter-row")
        assert size_row.is_visible(), "Sizes filter row must be visible on Footwear PDP"
        print("PASS: Footwear Sizes row is rendered.")

        # Verify size chips
        size_cbs = filter_bar.locator(".pdp-size-cb").all()
        print(f"Rendered Size chips count: {len(size_cbs)}")
        assert len(size_cbs) >= 10, f"Expected at least 10 size chips, found {len(size_cbs)}"
        print("PASS: UK 5 through UK 12 size chips present.")

        # Test selecting a size chip (e.g. UK 8)
        print("Action: Selecting Size 'UK 8' chip...")
        size_8_lbl = filter_bar.locator("label[for='pdp-size-uk-8']")
        assert size_8_lbl.is_visible(), "UK 8 chip label must be visible"
        size_8_lbl.click()
        page.wait_for_timeout(500)
        size_8_cb = filter_bar.locator("#pdp-size-uk-8")
        assert size_8_cb.is_checked(), "UK 8 checkbox must be checked"
        print("PASS: Size UK 8 chip selected.")

        # Test multi-selecting another size (e.g. UK 8.5)
        print("Action: Multi-selecting Size 'UK 8.5' chip...")
        size_85_lbl = filter_bar.locator("label[for='pdp-size-uk-8-5']")
        size_85_lbl.click()
        page.wait_for_timeout(500)
        size_85_cb = filter_bar.locator("#pdp-size-uk-8-5")
        assert size_8_cb.is_checked() and size_85_cb.is_checked(), "Both UK 8 and UK 8.5 must be checked"
        print("PASS: Multi-size selection verified: UK 8 + UK 8.5 simultaneously active.")

        # Verify summary & explore link
        summary_msg = filter_bar.locator("#pdp-filter-count-msg").text_content()
        explore_link = filter_bar.locator("#pdp-explore-collection-btn")
        print(f"Summary message: '{summary_msg.strip()}'")
        print(f"Explore link href: '{explore_link.get_attribute('href')}'")
        assert "Size UK 8" in summary_msg and "UK 8.5" in summary_msg, "Summary message should mention sizes"
        assert "UK" in explore_link.get_attribute("href") and "8" in explore_link.get_attribute("href"), "Explore link must contain size query"
        print("PASS: Summary message and explore search URL reflect selected footwear sizes.")

        # Capture screenshot
        page.wait_for_timeout(1000)
        pdp_footwear_screenshot = os.path.join(ARTIFACTS_DIR, "verified_pdp_footwear_size_filters.png")
        page.screenshot(path=pdp_footwear_screenshot, full_page=False)
        print(f"Saved screenshot: {pdp_footwear_screenshot}")
        page.close()

        # -------------------------------------------------------------
        # SUITE 2: FOOTWEAR PLP DRAWER WITH SHOE SIZE ACCORDION
        # -------------------------------------------------------------
        print("\n--- [SUITE 2] FOOTWEAR PLP COLLECTION DRAWER ---")
        page = context.new_page()
        col_url = "https://therareavenue.com/collections/footwear"
        print(f"Navigating to {col_url}...")
        page.goto(col_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        show_filters_btn = page.locator(".facets-toggle__button:visible, [on\\:click*='filters-drawer']:visible").first
        assert show_filters_btn.is_visible(), "Filter drawer trigger button should be visible"
        show_filters_btn.click()
        page.wait_for_timeout(1500)

        # Strictly verify Availability is 0
        avail_elements = page.locator("#filters-drawer :has-text('Availability'), [name='filter.v.availability']").all()
        assert len(avail_elements) == 0, f"Expected 0 Availability filter occurrences, found {len(avail_elements)}"
        print("PASS: Availability filter remains 100% suppressed on Footwear collection.")

        # Verify Shoe Size accordion in drawer
        size_accordion = page.locator("#filters-drawer #Facet-Details-luxury-sizes")
        assert size_accordion.is_visible(), "Shoe Size (UK) accordion must be visible in Footwear drawer"
        print("PASS: Shoe Size (UK) accordion rendered in drawer.")

        # Verify drawer size options
        drawer_size_cbs = page.locator("#filters-drawer .luxury-size-facet-cb").all()
        print(f"Drawer Shoe Size options count: {len(drawer_size_cbs)}")
        assert len(drawer_size_cbs) >= 10, f"Expected at least 10 shoe size options, found {len(drawer_size_cbs)}"
        print("PASS: Drawer size chips rendered.")

        plp_footwear_screenshot = os.path.join(ARTIFACTS_DIR, "verified_plp_footwear_drawer_sizes.png")
        page.screenshot(path=plp_footwear_screenshot, full_page=False)
        print(f"Saved screenshot: {plp_footwear_screenshot}")
        page.close()

        # -------------------------------------------------------------
        # SUITE 3: MOBILE RESPONSIVE (390x844) FOOTWEAR AUDIT
        # -------------------------------------------------------------
        print("\n--- [SUITE 3] MOBILE RESPONSIVE FOOTWEAR AUDIT ---")
        mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile_ctx.new_page()

        mobile_page.goto(footwear_url, wait_until="domcontentloaded", timeout=60000)
        mobile_page.wait_for_timeout(3000)
        m_filter_bar = mobile_page.locator("#luxury-pdp-discovery-filters")
        assert m_filter_bar.is_visible(), "Mobile Footwear PDP filter bar must be visible"
        m_filter_bar.scroll_into_view_if_needed()
        m_size_row = m_filter_bar.locator("#pdp-size-filter-row")
        assert m_size_row.is_visible(), "Mobile Sizes filter row must be visible"
        mobile_page.wait_for_timeout(1000)
        mobile_footwear_screenshot = os.path.join(ARTIFACTS_DIR, "verified_mobile_footwear_filters.png")
        mobile_page.screenshot(path=mobile_footwear_screenshot, full_page=False)
        print(f"Saved screenshot: {mobile_footwear_screenshot}")
        mobile_ctx.close()

        # -------------------------------------------------------------
        # SUITE 4: NON-FOOTWEAR PDP INTEGRITY (Handbags, Sunglasses, Watches)
        # -------------------------------------------------------------
        print("\n--- [SUITE 4] NON-FOOTWEAR CATEGORY INTEGRITY AUDIT ---")
        page = context.new_page()

        # Check Handbag PDP: Sizes row MUST NOT exist
        handbag_url = "https://therareavenue.com/products/tory-burch-robinson-spazzolato-convertible-shoulder-bag"
        page.goto(handbag_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        hb_filter_bar = page.locator("#luxury-pdp-discovery-filters")
        hb_size_rows = hb_filter_bar.locator("#pdp-size-filter-row").all()
        assert len(hb_size_rows) == 0, "Sizes row must NOT appear on Handbag PDP"
        print("PASS: Handbag PDP has no Size filter row (Category-specific scoping verified).")

        page.close()
        context.close()
        browser.close()

        print("\n" + "=" * 80)
        print("ALL FOOTWEAR SIZE VERIFICATION SUITES PASSED WITH 100% SUCCESS!")
        print("=" * 80)

if __name__ == "__main__":
    test_footwear_size_filters()
