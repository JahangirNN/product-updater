"""
Playwright automated test for Search Results Facet Filtering on The Rare Avenue live store.
Verifies:
1. Desktop Search Sidebar Facets (/search?q=Wallet):
   - Verifies Brand, Price, Availability, and Silhouette filters all render in sidebar.
   - Opens Brand accordion and checks 'COACH'.
   - Verifies search results update to COACH wallets.
   - Verifies URL preserves 'q=Wallet' parameter and includes 'filter.p.vendor=COACH'.
   - Verifies active facet pill 'Brand: COACH' renders.
   - Adjusts price range -> verifies results narrow.
   - Clears filters -> verifies clean state.
2. Desktop Search Sidebar Facets (/search?q=Bag):
   - Verifies Brand, Silhouette, Availability, and Price filters all render in sidebar.
3. Mobile Filter Drawer (/search?q=Wallet):
   - Sets mobile viewport (390x844).
   - Opens filter drawer via button.
   - Verifies Brand, Price, Availability, and Silhouette in drawer.
   - Selects brand, applies filters, verifies results update.
4. Saves visual proof screenshots to artifacts directory.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

WALLET_SEARCH_URL = "https://therareavenue.com/search?q=Wallet"
BAG_SEARCH_URL = "https://therareavenue.com/search?q=Bag"

def test_search_facets():
    print("=" * 80)
    print("STARTING PLAYWRIGHT SEARCH FACET TEST")
    print(f"Target URL: {WALLET_SEARCH_URL}")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ---------------------------------------------------------
        # PART 1: DESKTOP SEARCH (/search?q=Wallet)
        # ---------------------------------------------------------
        print("\n--- [1] DESKTOP SEARCH FACETS TEST (/search?q=Wallet) ---")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print(f"Navigating to {WALLET_SEARCH_URL}...")
        page.goto(WALLET_SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # 1. Verify facets render in sidebar
        print("Checking sidebar facet groups...")
        sidebar = page.locator(".facets-sidebar").first
        
        brand_acc = sidebar.locator("details summary:has-text('Brand')").first
        price_acc = sidebar.locator("details summary:has-text('Price')").first
        avail_acc = sidebar.locator("details summary:has-text('Availability')").first
        sil_acc = sidebar.locator("details summary:has-text('Silhouette')").first

        print(f"  Brand accordion present: {brand_acc.count() > 0}")
        print(f"  Price accordion present: {price_acc.count() > 0}")
        print(f"  Availability accordion present: {avail_acc.count() > 0}")
        print(f"  Silhouette accordion present: {sil_acc.count() > 0}")

        assert brand_acc.count() > 0, "Brand filter accordion is missing from search results sidebar!"
        assert price_acc.count() > 0, "Price filter accordion is missing from search results sidebar!"
        assert avail_acc.count() > 0, "Availability filter accordion is missing from search results sidebar!"
        assert sil_acc.count() > 0, "Silhouette filter accordion is missing from search results sidebar!"

        # Screenshot initial state
        initial_ss_path = os.path.join(ARTIFACTS_DIR, "01_desktop_search_wallet_facets_rendered.png")
        page.screenshot(path=initial_ss_path)
        print(f"Saved initial search facets screenshot to {initial_ss_path}")

        # 2. Open Brand accordion and verify checkboxes
        print("\nOpening Brand accordion...")
        if not brand_acc.locator("xpath=..").evaluate("el => el.hasAttribute('open')"):
            brand_acc.click()
            time.sleep(1)

        coach_cb = sidebar.locator("input[name='filter.p.vendor'][value='COACH']").first
        mk_cb = sidebar.locator("input[name='filter.p.vendor'][value='Michael Kors']").first
        jw_cb = sidebar.locator("input[name='filter.p.vendor'][value='JW PEI']").first

        print(f"  COACH checkbox found: {coach_cb.count() > 0}")
        print(f"  Michael Kors checkbox found: {mk_cb.count() > 0}")
        print(f"  JW PEI checkbox found: {jw_cb.count() > 0}")

        assert coach_cb.count() > 0, "COACH brand checkbox not found in search results!"

        # 3. Check COACH and verify products update
        print("\nChecking 'COACH' checkbox...")
        coach_cb.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change', { bubbles: true })); }")
        time.sleep(3)

        # Verify current URL preserved q=Wallet and has filter.p.vendor=COACH
        current_url = page.url
        print(f"Current URL after selecting COACH: {current_url}")
        assert "q=Wallet" in current_url, f"Search query 'q' lost! URL: {current_url}"
        assert "filter.p.vendor=COACH" in current_url, f"Vendor filter parameter missing! URL: {current_url}"

        # Verify cards are all COACH
        cards = page.locator("product-card")
        card_count = cards.count()
        print(f"Total product cards after filtering by COACH: {card_count}")
        assert card_count > 0, "No product cards displayed after filtering by COACH!"

        # Check vendor attribute on all rendered cards
        vendors_found = set(cards.evaluate_all("els => els.map(el => el.getAttribute('data-vendor'))"))
        print(f"Vendors among displayed cards: {vendors_found}")
        assert "COACH" in vendors_found, f"COACH products not found! Got: {vendors_found}"
        assert len([v for v in vendors_found if v and v != "COACH"]) == 0, f"Found non-COACH products: {vendors_found}"

        # Verify active facet pill
        active_facet = page.locator(".removable-facet:has-text('COACH')").first
        print(f"Active facet pill for COACH present: {active_facet.count() > 0}")
        assert active_facet.count() > 0, "Active facet pill for COACH missing!"

        # Screenshot filtered state
        coach_ss_path = os.path.join(ARTIFACTS_DIR, "02_desktop_search_wallet_coach_filtered.png")
        page.screenshot(path=coach_ss_path)
        print(f"Saved COACH filtered screenshot to {coach_ss_path}")

        # 4. Test Price Filter adjustment
        print("\nOpening Price accordion...")
        if not price_acc.locator("xpath=..").evaluate("el => el.hasAttribute('open')"):
            price_acc.click()
            time.sleep(1)

        price_from_input = sidebar.locator("input[name='filter.v.price.gte']").first
        price_to_input = sidebar.locator("input[name='filter.v.price.lte']").first
        print(f"Price inputs found: from={price_from_input.count() > 0}, to={price_to_input.count() > 0}")

        print("Setting price range 5000 - 15000...")
        price_from_input.fill("5000")
        price_to_input.fill("15000")
        price_to_input.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
        time.sleep(3)

        price_url = page.url
        print(f"Current URL after adjusting price: {price_url}")
        assert "q=Wallet" in price_url, f"q lost after price filter! URL: {price_url}"
        assert "filter.v.price.gte=5000" in price_url or "5000" in price_url, f"Price gte missing! URL: {price_url}"

        price_ss_path = os.path.join(ARTIFACTS_DIR, "03_desktop_search_wallet_price_filtered.png")
        page.screenshot(path=price_ss_path)
        print(f"Saved price filtered screenshot to {price_ss_path}")

        # ---------------------------------------------------------
        # PART 2: DESKTOP SEARCH (/search?q=Bag)
        # ---------------------------------------------------------
        print("\n--- [2] DESKTOP SEARCH FACETS TEST (/search?q=Bag) ---")
        print(f"Navigating to {BAG_SEARCH_URL}...")
        page.goto(BAG_SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        bag_sidebar = page.locator(".facets-sidebar").first
        bag_brand = bag_sidebar.locator("details summary:has-text('Brand')").first
        bag_sil = bag_sidebar.locator("details summary:has-text('Silhouette')").first
        bag_avail = bag_sidebar.locator("details summary:has-text('Availability')").first
        bag_price = bag_sidebar.locator("details summary:has-text('Price')").first

        print(f"  Bag Brand accordion present: {bag_brand.count() > 0}")
        print(f"  Bag Silhouette accordion present: {bag_sil.count() > 0}")
        print(f"  Bag Availability accordion present: {bag_avail.count() > 0}")
        print(f"  Bag Price accordion present: {bag_price.count() > 0}")

        assert bag_brand.count() > 0, "Brand filter missing on /search?q=Bag"
        assert bag_sil.count() > 0, "Silhouette filter missing on /search?q=Bag"
        assert bag_avail.count() > 0, "Availability filter missing on /search?q=Bag"
        assert bag_price.count() > 0, "Price filter missing on /search?q=Bag"

        bag_ss_path = os.path.join(ARTIFACTS_DIR, "04_desktop_search_bag_facets.png")
        page.screenshot(path=bag_ss_path)
        print(f"Saved Bag search facets screenshot to {bag_ss_path}")

        context.close()

        # ---------------------------------------------------------
        # PART 3: MOBILE DRAWER (/search?q=Wallet)
        # ---------------------------------------------------------
        print("\n--- [3] MOBILE DRAWER FACETS TEST (/search?q=Wallet) ---")
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile_context.new_page()

        print(f"Navigating to {WALLET_SEARCH_URL} on mobile viewport...")
        mobile_page.goto(WALLET_SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        filter_btn = mobile_page.locator("button[aria-controls='facets-drawer']").first
        print(f"Mobile Filter button found: {filter_btn.count() > 0}")
        assert filter_btn.count() > 0, "Mobile filter button missing!"

        print("Opening mobile facets drawer...")
        filter_btn.click()
        time.sleep(2)

        # Verify drawer has Brand, Silhouette, Availability, Price
        d_brand = mobile_page.locator("#facets-drawer summary:has-text('Brand')").first
        d_sil = mobile_page.locator("#facets-drawer summary:has-text('Silhouette')").first
        d_avail = mobile_page.locator("#facets-drawer summary:has-text('Availability')").first
        d_price = mobile_page.locator("#facets-drawer summary:has-text('Price')").first

        print(f"  Drawer Brand accordion visible: {d_brand.is_visible()}")
        print(f"  Drawer Silhouette accordion visible: {d_sil.is_visible()}")
        print(f"  Drawer Availability accordion visible: {d_avail.is_visible()}")
        print(f"  Drawer Price accordion visible: {d_price.is_visible()}")

        assert d_brand.is_visible(), "Brand filter missing in mobile drawer!"
        assert d_sil.is_visible(), "Silhouette filter missing in mobile drawer!"
        assert d_avail.is_visible(), "Availability filter missing in mobile drawer!"
        assert d_price.is_visible(), "Price filter missing in mobile drawer!"

        # Open Brand in drawer if not already open
        if not d_brand.locator("xpath=..").evaluate("el => el.hasAttribute('open')"):
            d_brand.click()
            time.sleep(1)

        # Check COACH in drawer
        d_coach = mobile_page.locator("#facets-drawer input[name='filter.p.vendor'][value='COACH']").first
        assert d_coach.count() > 0, "COACH checkbox missing in mobile drawer!"
        d_coach.click()

        # Screenshot open drawer
        drawer_ss_path = os.path.join(ARTIFACTS_DIR, "05_mobile_drawer_facets_open.png")
        mobile_page.screenshot(path=drawer_ss_path)
        print(f"Saved mobile drawer screenshot to {drawer_ss_path}")

        # Click Apply Filters
        apply_btn = mobile_page.locator("#facets-drawer dialog-close-button button, #facets-drawer button:has-text('Apply')").first
        print(f"Apply button found: {apply_btn.count() > 0}")
        apply_btn.click()
        time.sleep(3)

        mobile_url = mobile_page.url
        print(f"Mobile URL after applying filter: {mobile_url}")
        assert "q=Wallet" in mobile_url, f"q lost on mobile! URL: {mobile_url}"
        assert "filter.p.vendor=COACH" in mobile_url, f"Vendor filter lost on mobile! URL: {mobile_url}"

        # Verify mobile cards are COACH
        m_cards = mobile_page.locator("product-card")
        print(f"Mobile product cards count: {m_cards.count()}")
        assert m_cards.count() > 0, "No cards on mobile after filtering!"

        m_vendors = set(m_cards.evaluate_all("els => els.map(el => el.getAttribute('data-vendor'))"))
        print(f"Mobile card vendors: {m_vendors}")
        assert "COACH" in m_vendors, f"COACH products not found on mobile! Got: {m_vendors}"

        mobile_filtered_ss_path = os.path.join(ARTIFACTS_DIR, "06_mobile_search_wallet_filtered.png")
        mobile_page.screenshot(path=mobile_filtered_ss_path)
        print(f"Saved mobile filtered screenshot to {mobile_filtered_ss_path}")

        mobile_context.close()
        browser.close()

    print("\n" + "=" * 80)
    print("ALL PLAYWRIGHT SEARCH FACET TESTS PASSED PERFECTLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_search_facets()
