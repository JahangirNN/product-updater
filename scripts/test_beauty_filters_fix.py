import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def test_beauty_filters():
    print("=" * 80)
    print("STARTING PLAYWRIGHT BEAUTY FILTER VERIFICATION SUITE")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)

        # -------------------------------------------------------------
        # SUITE 1: BEAUTY COLLECTION DRAWER (/collections/beauty)
        # -------------------------------------------------------------
        print("\n--- [SUITE 1] BEAUTY COLLECTION DRAWER AUDIT ---")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        beauty_col_url = "https://therareavenue.com/collections/beauty"
        print(f"Navigating to {beauty_col_url}...")
        page.goto(beauty_col_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        show_filters_btn = page.locator(".facets-toggle__button:visible, [on\\:click*='filters-drawer']:visible").first
        assert show_filters_btn.is_visible(), "Filter drawer trigger button should be visible"
        show_filters_btn.click()
        page.wait_for_timeout(1500)

        # 1. STRICT ASSERTION: Handbag brands must NOT exist in Beauty drawer!
        coach_elements = page.locator("#filters-drawer input[value='COACH'], #filters-drawer :text-is('COACH')").all()
        mj_elements = page.locator("#filters-drawer input[value='Marc Jacobs']").all()
        print(f"Handbag brand 'COACH' occurrences in Beauty drawer: {len(coach_elements)}")
        assert len(coach_elements) == 0, f"REGRESSION: Found {len(coach_elements)} COACH elements in Beauty drawer!"
        assert len(mj_elements) == 0, f"REGRESSION: Found {len(mj_elements)} Marc Jacobs elements in Beauty drawer!"
        print("PASS: Handbag brands (COACH, Marc Jacobs, etc.) are 100% REMOVED from Beauty drawer!")

        # 2. STRICT ASSERTION: Beauty brands must be rendered!
        drawer_brands = page.locator("#filters-drawer .luxury-brand-facet-cb").all()
        rendered_brand_names = [b.get_attribute("value") for b in drawer_brands]
        print(f"Rendered Beauty brands in drawer ({len(rendered_brand_names)}):")
        print("  ", ", ".join(rendered_brand_names))
        assert "rhode" in rendered_brand_names, "rhode should be in Beauty drawer"
        assert "Saie" in rendered_brand_names, "Saie should be in Beauty drawer"
        assert "Summer Fridays" in rendered_brand_names, "Summer Fridays should be in Beauty drawer"
        assert "Hourglass" in rendered_brand_names, "Hourglass should be in Beauty drawer"
        print("PASS: Authentic Beauty brands properly rendered in drawer.")

        # 3. Category pills check (All Beauty, Makeup, Skincare, Haircare, Gift Sets)
        category_pills = page.locator("#filters-drawer .luxury-gender-pill").all()
        cat_texts = [p.text_content().strip() for p in category_pills]
        print(f"Category pills rendered in drawer: {cat_texts}")
        assert "All Beauty" in cat_texts and "Makeup" in cat_texts and "Skincare" in cat_texts, "Beauty categories must be rendered"
        print("PASS: Quiet luxury Beauty category pills rendered.")

        # 4. Availability strictly 0
        avail = page.locator("#filters-drawer :has-text('Availability'), [name='filter.v.availability']").all()
        assert len(avail) == 0, "Availability filter must remain 0"
        print("PASS: Availability filter strictly suppressed (0 occurrences).")

        drawer_screenshot = os.path.join(ARTIFACTS_DIR, "verified_beauty_drawer_fixed.png")
        page.screenshot(path=drawer_screenshot, full_page=False)
        print(f"Saved screenshot: {drawer_screenshot}")
        page.close()

        # -------------------------------------------------------------
        # SUITE 2: BEAUTY PDP (rhode peptide lip treatment)
        # -------------------------------------------------------------
        print("\n--- [SUITE 2] BEAUTY PDP DISCOVERY FILTERS ---")
        page = context.new_page()
        rhode_url = "https://therareavenue.com/products/rhode-peptide-lip-treatment-nourishing-glaze-p517486"
        print(f"Navigating to {rhode_url}...")
        page.goto(rhode_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        filter_bar = page.locator("#luxury-pdp-discovery-filters")
        assert filter_bar.is_visible(), "PDP Discovery Filter Bar should be visible on Beauty PDP"
        filter_bar.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        # Confirm Handbag brands NOT on Beauty PDP
        pdp_coach = filter_bar.locator("input[value='COACH']").all()
        assert len(pdp_coach) == 0, "COACH should NOT appear on Beauty PDP"
        print("PASS: Handbag brands are NOT rendered on Beauty PDP.")

        # Confirm Beauty brands rendered on PDP
        pdp_rhode = filter_bar.locator("label[for='pdp-cb-rhode']")
        pdp_saie = filter_bar.locator("label[for='pdp-cb-saie']")
        assert pdp_rhode.is_visible() and pdp_saie.is_visible(), "rhode and Saie must be visible on Beauty PDP"
        print("PASS: Beauty atelier chips (rhode, Saie, etc.) rendered on Beauty PDP.")

        # Confirm Explore link
        explore_btn = filter_bar.locator("#pdp-explore-collection-btn")
        print(f"PDP Explore button text: '{explore_btn.text_content().strip()}'")
        print(f"PDP Explore button href: '{explore_btn.get_attribute('href')}'")
        assert "Beauty" in explore_btn.text_content(), "Explore link should refer to Beauty"
        assert "/collections/beauty" in explore_btn.get_attribute("href"), "Explore link should point to /collections/beauty"
        print("PASS: Explore button correctly links to Beauty.")

        # Multi-select rhode + Saie
        print("Action: Multi-selecting rhode + Saie...")
        pdp_rhode.click()
        page.wait_for_timeout(500)
        pdp_saie.click()
        page.wait_for_timeout(500)

        rhode_cb = filter_bar.locator("#pdp-cb-rhode")
        saie_cb = filter_bar.locator("#pdp-cb-saie")
        assert rhode_cb.is_checked() and saie_cb.is_checked(), "Both rhode and Saie must be checked"
        print("PASS: Multi-brand selection verified for Beauty.")

        summary_msg = filter_bar.locator("#pdp-filter-count-msg").text_content()
        print(f"Beauty summary message: '{summary_msg.strip()}'")
        assert "rhode" in summary_msg and "Saie" in summary_msg, "Summary should mention rhode and Saie"

        page.wait_for_timeout(1000)
        pdp_screenshot = os.path.join(ARTIFACTS_DIR, "verified_beauty_pdp_fixed.png")
        page.screenshot(path=pdp_screenshot, full_page=False)
        print(f"Saved screenshot: {pdp_screenshot}")
        page.close()

        # -------------------------------------------------------------
        # SUITE 3: MOBILE RESPONSIVE (390x844) BEAUTY DRAWER
        # -------------------------------------------------------------
        print("\n--- [SUITE 3] MOBILE RESPONSIVE BEAUTY DRAWER AUDIT ---")
        mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile_ctx.new_page()

        mobile_page.goto(beauty_col_url, wait_until="domcontentloaded", timeout=60000)
        mobile_page.wait_for_timeout(3000)

        m_btn = mobile_page.locator(".facets-toggle__button:visible, [on\\:click*='filters-drawer']:visible").first
        m_btn.click()
        mobile_page.wait_for_timeout(1500)

        m_coach = mobile_page.locator("#filters-drawer input[value='COACH']").all()
        assert len(m_coach) == 0, "COACH must not appear on mobile beauty drawer"
        m_rhode = mobile_page.locator("#filters-drawer input[value='rhode']")
        assert m_rhode.count() > 0, "rhode must appear on mobile beauty drawer"

        mobile_drawer_screenshot = os.path.join(ARTIFACTS_DIR, "verified_mobile_beauty_drawer.png")
        mobile_page.screenshot(path=mobile_drawer_screenshot, full_page=False)
        print(f"Saved screenshot: {mobile_drawer_screenshot}")
        mobile_ctx.close()

        # -------------------------------------------------------------
        # SUITE 4: HANDBAG COLLECTION INTEGRITY AUDIT
        # -------------------------------------------------------------
        print("\n--- [SUITE 4] HANDBAG COLLECTION INTEGRITY AUDIT ---")
        page = context.new_page()
        hb_url = "https://therareavenue.com/collections/womens-handbags"
        page.goto(hb_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        hb_btn = page.locator(".facets-toggle__button:visible, [on\\:click*='filters-drawer']:visible").first
        hb_btn.click()
        page.wait_for_timeout(1500)

        hb_coach = page.locator("#filters-drawer input[value='COACH']").all()
        assert len(hb_coach) > 0, "COACH should appear on Handbag drawer"
        print("PASS: Handbag collection drawer properly preserves Handbag brands (COACH, etc.).")

        page.close()
        context.close()
        browser.close()

        print("\n" + "=" * 80)
        print("ALL BEAUTY FILTER VERIFICATION SUITES PASSED WITH 100% SUCCESS!")
        print("=" * 80)

if __name__ == "__main__":
    test_beauty_filters()
