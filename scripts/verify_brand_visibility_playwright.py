import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLLECTIONS_TO_TEST = [
    {
        "name": "designer_eyewear",
        "url": "https://therareavenue.com/collections/designer-eyewear",
        "title": "Designer Sunglasses & Eyewear"
    },
    {
        "name": "womens_sunglasses",
        "url": "https://therareavenue.com/collections/womens-sunglasses",
        "title": "Women's Sunglasses"
    },
    {
        "name": "luxury_watches",
        "url": "https://therareavenue.com/collections/luxury-watches",
        "title": "Luxury Watches"
    },
    {
        "name": "designer_bags",
        "url": "https://therareavenue.com/collections/designer-bags",
        "title": "Designer Bags"
    }
]

def run_brand_visibility_verification():
    print("=" * 80)
    print("STARTING PLAYWRIGHT BRAND VISIBILITY VERIFICATION")
    print(f"Artifacts output dir: {OUTPUT_DIR}")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for col in COLLECTIONS_TO_TEST:
            col_name = col["name"]
            url = col["url"]

            # --- DESKTOP VIEWPORT ---
            print(f"\n[DESKTOP] Testing {url}...", flush=True)
            context_desktop = browser.new_context(viewport={"width": 1440, "height": 900})
            page_desktop = context_desktop.new_page()

            page_desktop.goto(url, wait_until="domcontentloaded", timeout=30000)
            page_desktop.wait_for_selector(".product-card", timeout=15000)
            page_desktop.wait_for_timeout(2000)

            cards = page_desktop.locator(".product-card")
            card_count = cards.count()
            print(f"  Found {card_count} product cards.")

            # Check vendor elements
            vendor_elements = page_desktop.locator(".product-card .vendor")
            vendor_count = vendor_elements.count()
            print(f"  Found {vendor_count} vendor elements inside product cards.")

            if card_count > 0:
                assert vendor_count > 0, f"Expected vendors on product cards in {col_name}, found 0!"
                # Sample the first 4 cards
                sample_count = min(card_count, 6)
                for idx in range(sample_count):
                    card = cards.nth(idx)
                    v_elem = card.locator(".vendor")
                    v_text = v_elem.inner_text().strip() if v_elem.count() > 0 else "MISSING"
                    t_elem = card.locator(".product-title")
                    t_text = t_elem.inner_text().strip() if t_elem.count() > 0 else "NO TITLE"
                    v_visible = v_elem.is_visible() if v_elem.count() > 0 else False
                    print(f"    Card #{idx+1}: Brand='{v_text}' | Title='{t_text}' | Visible={v_visible}")

            desktop_screenshot = os.path.join(OUTPUT_DIR, f"{col_name}_desktop_brand_visible.png")
            page_desktop.screenshot(path=desktop_screenshot, full_page=False)
            print(f"  Saved Desktop screenshot: {desktop_screenshot}")
            context_desktop.close()

            # --- MOBILE VIEWPORT ---
            print(f"\n[MOBILE] Testing {url}...", flush=True)
            context_mobile = browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            )
            page_mobile = context_mobile.new_page()

            page_mobile.goto(url, wait_until="domcontentloaded", timeout=30000)
            page_mobile.wait_for_selector(".product-card", timeout=15000)
            page_mobile.wait_for_timeout(2000)

            m_cards = page_mobile.locator(".product-card")
            m_card_count = m_cards.count()
            m_vendors = page_mobile.locator(".product-card .vendor")
            m_vendor_count = m_vendors.count()
            print(f"  [Mobile] Found {m_card_count} product cards, {m_vendor_count} vendor labels.", flush=True)

            if m_card_count > 0:
                assert m_vendor_count > 0, f"Expected mobile vendors on product cards in {col_name}!"
                sample_count = min(m_card_count, 3)
                for idx in range(sample_count):
                    card = m_cards.nth(idx)
                    v_elem = card.locator(".vendor")
                    v_text = v_elem.inner_text().strip() if v_elem.count() > 0 else "MISSING"
                    v_visible = v_elem.is_visible() if v_elem.count() > 0 else False
                    print(f"    Mobile Card #{idx+1}: Brand='{v_text}' | Visible={v_visible}", flush=True)

            mobile_screenshot = os.path.join(OUTPUT_DIR, f"{col_name}_mobile_brand_visible.png")
            page_mobile.screenshot(path=mobile_screenshot, full_page=False)
            print(f"  Saved Mobile screenshot: {mobile_screenshot}", flush=True)
            context_mobile.close()

        # --- PDP VERIFICATION ---
        print("\n[PDP] Verifying Product Details Page...", flush=True)
        pdp_context = browser.new_context(viewport={"width": 1440, "height": 900})
        pdp_page = pdp_context.new_page()
        # Find sunglasses product link from eyewear collection
        pdp_page.goto("https://therareavenue.com/collections/designer-eyewear", wait_until="domcontentloaded", timeout=30000)
        pdp_page.wait_for_selector(".product-card", timeout=15000)
        pdp_page.wait_for_timeout(2000)
        first_card_link = pdp_page.locator(".product-card a.product-card__media").first.get_attribute("href")
        if first_card_link:
            full_pdp_url = f"https://therareavenue.com{first_card_link}" if first_card_link.startswith("/") else first_card_link
            print(f"  Navigating to PDP: {full_pdp_url}", flush=True)
            pdp_page.goto(full_pdp_url, wait_until="domcontentloaded", timeout=30000)
            pdp_page.wait_for_selector(".luxury-pdp-maison", timeout=15000)
            pdp_page.wait_for_timeout(2000)

            maison_tag = pdp_page.locator(".luxury-pdp-maison__tag").inner_text().strip()
            maison_vendor = pdp_page.locator(".luxury-pdp-maison__vendor").inner_text().strip()
            vendor_href = pdp_page.locator(".luxury-pdp-maison__vendor").get_attribute("href")
            print(f"  PDP Maison Tag: '{maison_tag}'", flush=True)
            print(f"  PDP Maison Vendor: '{maison_vendor}' -> Link: '{vendor_href}'", flush=True)

            pdp_screenshot = os.path.join(OUTPUT_DIR, "sunglasses_pdp_brand_visible.png")
            pdp_page.screenshot(path=pdp_screenshot, full_page=False)
            print(f"  Saved PDP screenshot: {pdp_screenshot}", flush=True)

        pdp_context.close()
        browser.close()
        print("\nALL PLAYWRIGHT TESTS PASSED!", flush=True)

if __name__ == "__main__":
    run_brand_visibility_verification()
