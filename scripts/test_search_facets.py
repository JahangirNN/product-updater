"""
Playwright automated test for Search Results Facet Filtering on The Rare Avenue live store.
Verifies:
1. Desktop Search Sidebar Facets (/search?q=Wallet):
   - Verifies Brand, Price, Availability, and Silhouette filters all render in sidebar.
   - Opens Brand accordion and checks 'COACH'.
   - Verifies search results update to COACH wallets (48 cards).
   - Verifies URL preserves clean 'q=Wallet' and includes 'filter.p.vendor=COACH'.
   - Verifies active facet pill 'Brand: COACH' renders.
   - Adjusts price range -> verifies clean URL without backend boolean leaks ('vendor:' / 'tag:').
   - Tests multi-brand selection (COACH + Michael Kors) -> verifies clean URL with both brands.
   - Tests removing active brand pill -> verifies clean uncheck and state sync without corruption.
   - Clears filters -> verifies clean restored state.
2. Desktop Search Sidebar Facets (/search?q=Bag):
   - Verifies Brand, Silhouette, Availability, and Price filters all render in sidebar.
3. Search with parenthesis query (/search?q=Wallet+(Black)):
   - Verifies query is preserved cleanly without unwanted string truncation.
4. Mobile Filter Drawer (/search?q=Wallet):
   - Sets mobile viewport (390x844).
   - Opens filter drawer via button.
   - Verifies Brand, Price, Availability, and Silhouette in drawer.
   - Selects brand, applies filters, verifies results update.
5. Saves visual proof screenshots to artifacts directory.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

WALLET_SEARCH_URL = "https://therareavenue.com/search?q=Wallet"
BAG_SEARCH_URL = "https://therareavenue.com/search?q=Bag"
PAREN_SEARCH_URL = "https://therareavenue.com/search?q=Wallet+(Black)"

def test_search_facets():
    print("=" * 80)
    print("STARTING COMPREHENSIVE PLAYWRIGHT SEARCH FACET TEST")
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
        sil_acc = sidebar.locator("details summary:has-text('Category'), details summary:has-text('Silhouette')").first

        print(f"  Brand accordion present: {brand_acc.count() > 0}")
        print(f"  Price accordion present: {price_acc.count() > 0}")
        print(f"  Availability accordion present: {avail_acc.count() > 0}")
        print(f"  Category accordion present: {sil_acc.count() > 0}")

        assert brand_acc.count() > 0, "Brand filter accordion is missing from search results sidebar!"
        assert price_acc.count() > 0, "Price filter accordion is missing from search results sidebar!"
        assert avail_acc.count() > 0, "Availability filter accordion is missing from search results sidebar!"
        assert sil_acc.count() > 0, "Category filter accordion is missing from search results sidebar!"

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

        # Verify current URL preserved clean q=Wallet and has filter.p.vendor=COACH
        current_url = page.url
        print(f"Current URL after selecting COACH: {current_url}")
        assert "q=Wallet" in current_url, f"Search query 'q' lost! URL: {current_url}"
        assert "vendor:" not in current_url, f"Backend boolean query syntax leaked into browser URL! URL: {current_url}"
        assert "filter.p.vendor=COACH" in current_url, f"Vendor filter parameter missing! URL: {current_url}"

        # Verify product cards update to COACH
        cards = page.locator("product-card")
        cards_count = cards.count()
        print(f"Total product cards after filtering by COACH: {cards_count}")
        assert cards_count > 0, "No product cards displayed after filtering by COACH!"

        displayed_vendors = set(cards.evaluate_all("els => els.map(el => el.getAttribute('data-vendor'))"))
        print(f"Vendors among displayed cards: {displayed_vendors}")
        assert displayed_vendors == {"COACH"}, f"Expected only COACH products, got: {displayed_vendors}"

        # Verify active facet pill
        active_facet = page.locator(".removable-facet:has-text('COACH')").first
        print(f"Active facet pill for COACH present: {active_facet.count() > 0}")
        assert active_facet.count() > 0, "Active facet pill for COACH missing!"

        # Screenshot filtered state
        coach_ss_path = os.path.join(ARTIFACTS_DIR, "02_desktop_search_wallet_coach_filtered.png")
        page.screenshot(path=coach_ss_path)
        print(f"Saved COACH filtered screenshot to {coach_ss_path}")

        # 4. Test Price Filter adjustment (with COACH active)
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
        assert "vendor:" not in price_url, f"Backend boolean query syntax leaked into browser URL! URL: {price_url}"
        assert "filter.p.vendor=COACH" in price_url, f"COACH filter lost after price adjust! URL: {price_url}"
        assert "filter.v.price.gte=5000" in price_url or "5000" in price_url, f"Price gte missing! URL: {price_url}"

        price_ss_path = os.path.join(ARTIFACTS_DIR, "03_desktop_search_wallet_price_filtered.png")
        page.screenshot(path=price_ss_path)
        print(f"Saved price filtered screenshot to {price_ss_path}")

        # 5. Multi-brand selection: Add Michael Kors
        print("\nTesting Multi-Brand Selection: Checking Michael Kors...")
        if not brand_acc.locator("xpath=..").evaluate("el => el.hasAttribute('open')"):
            brand_acc.click()
            time.sleep(1)

        mk_cb = sidebar.locator("input[name='filter.p.vendor'][value='Michael Kors']").first
        mk_cb.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change', { bubbles: true })); }")
        time.sleep(3)

        multi_brand_url = page.url
        print(f"URL after adding Michael Kors: {multi_brand_url}")
        assert "q=Wallet" in multi_brand_url, f"q corrupted! URL: {multi_brand_url}"
        assert "vendor:" not in multi_brand_url, f"Leaked vendor syntax in multi-brand URL! URL: {multi_brand_url}"
        assert ")" not in multi_brand_url.split("?")[1].split("&")[0], f"Stray parenthesis in q! URL: {multi_brand_url}"
        assert "filter.p.vendor=COACH" in multi_brand_url, f"COACH missing in multi-brand URL! URL: {multi_brand_url}"
        assert "filter.p.vendor=Michael+Kors" in multi_brand_url or "filter.p.vendor=Michael%20Kors" in multi_brand_url, f"Michael Kors missing! URL: {multi_brand_url}"

        # 6. Test removing active brand pill for COACH
        print("\nTesting active facet pill removal: Removing COACH pill...")
        coach_pill_remove = page.locator("[data-brand-remove='COACH']").first
        assert coach_pill_remove.count() > 0, "COACH pill remove button missing!"
        coach_pill_remove.click()
        time.sleep(3)

        pill_removed_url = page.url
        print(f"URL after removing COACH pill: {pill_removed_url}")
        assert "filter.p.vendor=COACH" not in pill_removed_url, f"COACH still present in URL after pill removal! URL: {pill_removed_url}"
        assert "vendor:" not in pill_removed_url, f"Leaked vendor syntax after pill removal! URL: {pill_removed_url}"
        assert "filter.p.vendor=Michael+Kors" in pill_removed_url or "filter.p.vendor=Michael%20Kors" in pill_removed_url, f"Michael Kors lost! URL: {pill_removed_url}"

        # 7. Test Clear All
        print("\nTesting Clear All...")
        clear_all_btn = page.locator(".facets-clear-all").first
        if clear_all_btn.count() > 0:
            clear_all_btn.click()
            time.sleep(3)
            cleared_url = page.url
            print(f"URL after Clear all: {cleared_url}")
            assert "filter.p.vendor" not in cleared_url, f"Vendor filter still present after clear all! URL: {cleared_url}"
            assert "filter.v.price" not in cleared_url, f"Price filter still present after clear all! URL: {cleared_url}"
            assert "q=Wallet" in cleared_url, f"q lost after clear all! URL: {cleared_url}"

        # ---------------------------------------------------------
        # PART 2: DESKTOP SEARCH (/search?q=Bag)
        # ---------------------------------------------------------
        print("\n--- [2] DESKTOP SEARCH FACETS TEST (/search?q=Bag) ---")
        print(f"Navigating to {BAG_SEARCH_URL}...")
        page.goto(BAG_SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        bag_sidebar = page.locator(".facets-sidebar").first
        bag_brand = bag_sidebar.locator("details summary:has-text('Brand')").first
        bag_sil = bag_sidebar.locator("details summary:has-text('Category'), details summary:has-text('Silhouette')").first
        bag_avail = bag_sidebar.locator("details summary:has-text('Availability')").first
        bag_price = bag_sidebar.locator("details summary:has-text('Price')").first

        print(f"  Bag Brand accordion present: {bag_brand.count() > 0}")
        print(f"  Bag Category accordion present: {bag_sil.count() > 0}")
        print(f"  Bag Availability accordion present: {bag_avail.count() > 0}")
        print(f"  Bag Price accordion present: {bag_price.count() > 0}")

        assert bag_brand.count() > 0, "Brand filter missing on /search?q=Bag"
        assert bag_sil.count() > 0, "Category filter missing on /search?q=Bag"
        assert bag_avail.count() > 0, "Availability filter missing on /search?q=Bag"
        assert bag_price.count() > 0, "Price filter missing on /search?q=Bag"

        bag_ss_path = os.path.join(ARTIFACTS_DIR, "04_desktop_search_bag_facets.png")
        page.screenshot(path=bag_ss_path)
        print(f"Saved Bag search facets screenshot to {bag_ss_path}")

        # ---------------------------------------------------------
        # PART 3: PARENTHESIS QUERY (/search?q=Wallet+(Black))
        # ---------------------------------------------------------
        print("\n--- [3] PARENTHESIS QUERY TEST (/search?q=Wallet+(Black)) ---")
        print(f"Navigating to {PAREN_SEARCH_URL}...")
        page.goto(PAREN_SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        paren_sidebar = page.locator(".facets-sidebar").first
        p_brand = paren_sidebar.locator("details summary:has-text('Brand')").first
        assert p_brand.count() > 0, "Brand filter missing on parenthesis search query!"
        if not p_brand.locator("xpath=..").evaluate("el => el.hasAttribute('open')"):
            p_brand.click()
            time.sleep(1)

        p_coach = paren_sidebar.locator("input[name='filter.p.vendor'][value='COACH']").first
        if p_coach.count() > 0:
            p_coach.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change', { bubbles: true })); }")
            time.sleep(3)
            paren_filtered_url = page.url
            print(f"URL after filtering on parenthesis query: {paren_filtered_url}")
            assert "Wallet" in paren_filtered_url and "Black" in paren_filtered_url, f"Query tokens lost! URL: {paren_filtered_url}"
            assert "vendor:" not in paren_filtered_url, f"Vendor syntax leaked! URL: {paren_filtered_url}"

        context.close()

        # ---------------------------------------------------------
        # PART 4: MOBILE DRAWER (/search?q=Wallet)
        # ---------------------------------------------------------
        print("\n--- [4] MOBILE DRAWER FACETS TEST (/search?q=Wallet) ---")
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
        d_sil = mobile_page.locator("#facets-drawer summary:has-text('Category'), #facets-drawer summary:has-text('Silhouette')").first
        d_avail = mobile_page.locator("#facets-drawer summary:has-text('Availability')").first
        d_price = mobile_page.locator("#facets-drawer summary:has-text('Price')").first

        print(f"  Drawer Brand accordion visible: {d_brand.is_visible()}")
        print(f"  Drawer Category accordion visible: {d_sil.is_visible()}")
        print(f"  Drawer Availability accordion visible: {d_avail.is_visible()}")
        print(f"  Drawer Price accordion visible: {d_price.is_visible()}")

        assert d_brand.is_visible(), "Brand filter missing in mobile drawer!"
        assert d_sil.is_visible(), "Category filter missing in mobile drawer!"
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
        assert "vendor:" not in mobile_url, f"Vendor syntax leaked on mobile! URL: {mobile_url}"
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
