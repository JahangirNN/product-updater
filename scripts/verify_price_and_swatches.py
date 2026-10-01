import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

URL = "https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI&filter.v.price.gte=15000&filter.v.price.lte=31560"

def run_verification():
    print("=" * 80)
    print("STARTING PLAYWRIGHT VISUAL VERIFICATION")
    print("Target URL:", URL)
    print("=" * 80)

    with sync_playwright() as p:
        # 1. Desktop Test (1440x900)
        print("\n--- 1. Testing Desktop (1440x900) ---")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("Navigating to URL on desktop...")
        page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        # Wait for dynamic vendor facet update and rendering
        page.wait_for_timeout(4000)

        # Check for product cards
        cards = page.query_selector_all("product-card")
        print(f"Total product cards found on desktop: {len(cards)}")

        # Collect and print prices for cards
        card_prices = []
        for i, card in enumerate(cards[:10]):
            handle = card.get_attribute("handle") or f"card-{i+1}"
            vendor = card.get_attribute("data-vendor") or "Unknown"
            price_el = card.query_selector("price-list")
            price_text = price_el.inner_text().replace("\n", " ").strip() if price_el else "NO PRICE"
            card_prices.append((handle, vendor, price_text))
            print(f"  [{i+1}] {handle} ({vendor}): {price_text}")

        # Verification checks
        no_old_from_price = True
        matching_price_found = False

        for handle, vendor, price_text in card_prices:
            if "9,497" in price_text and ("FROM" in price_text.upper() or "From" in price_text):
                print(f"  [ERROR] Card {handle} still displays 'FROM RS. 9,497.00'!")
                no_old_from_price = False
            if "16,235" in price_text or "16,212" in price_text or "15,274" in price_text or "19,117" in price_text:
                matching_price_found = True

        desktop_screenshot_path = os.path.join(OUTPUT_DIR, "desktop_price_filtering.png")
        page.screenshot(path=desktop_screenshot_path, full_page=False)
        print(f"Captured Desktop Screenshot -> {desktop_screenshot_path}")

        # 2. Test Swatch Interaction (Hover and Click)
        print("\n--- 2. Testing Swatch Hover & Click Interaction ---")
        swatch_card = None
        for card in cards:
            swatches = card.query_selector_all(".color-swatch")
            if len(swatches) >= 2:
                swatch_card = card
                break

        if swatch_card:
            card_handle = swatch_card.get_attribute("handle")
            print(f"Found card with multiple swatches: {card_handle}")
            price_el = swatch_card.query_selector("price-list")
            initial_price = price_el.inner_text().replace("\n", " ").strip() if price_el else ""
            print(f"Initial Card Price: {initial_price}")

            swatches = swatch_card.query_selector_all(".color-swatch")
            print(f"Total swatches on card: {len(swatches)}")

            # Scroll card into view
            swatch_card.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)

            # Check swatch attributes
            for idx, sw in enumerate(swatches[:4]):
                p_attr = sw.get_attribute("data-variant-price") or "none"
                print(f"  Swatch {idx+1} data-variant-price: {p_attr}")

            # Hover second swatch
            target_swatch = swatches[1]
            target_price_attr = target_swatch.get_attribute("data-variant-price") or ""

            target_swatch.hover()
            page.wait_for_timeout(800)

            hover_price = price_el.inner_text().replace("\n", " ").strip() if price_el else ""
            print(f"Price after hover on Swatch 2: {hover_price}")

            swatch_hover_screenshot = os.path.join(OUTPUT_DIR, "desktop_swatch_hover.png")
            swatch_card.screenshot(path=swatch_hover_screenshot)
            print(f"Captured Swatch Hover Screenshot -> {swatch_hover_screenshot}")

            # Click second swatch
            target_swatch.click()
            page.wait_for_timeout(800)
            click_price = price_el.inner_text().replace("\n", " ").strip() if price_el else ""
            print(f"Price after click on Swatch 2: {click_price}")

            # Hover third swatch
            if len(swatches) >= 3:
                swatches[2].hover()
                page.wait_for_timeout(800)
                hover_price_3 = price_el.inner_text().replace("\n", " ").strip() if price_el else ""
                print(f"Price after hover on Swatch 3: {hover_price_3}")
        else:
            print("No card with swatches found on initial view!")

        browser.close()

        # 3. Mobile Test (430x932 iPhone 14 Pro Max)
        print("\n--- 3. Testing Mobile (430x932) ---")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 430, "height": 932}, is_mobile=True, user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1")
        page = context.new_page()

        print("Navigating to URL on mobile...")
        page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        mobile_screenshot_path = os.path.join(OUTPUT_DIR, "mobile_price_filtering.png")
        page.screenshot(path=mobile_screenshot_path, full_page=False)
        print(f"Captured Mobile Screenshot -> {mobile_screenshot_path}")

        # Check mobile cards
        mobile_cards = page.query_selector_all("product-card")
        print(f"Total product cards on mobile: {len(mobile_cards)}")
        for i, card in enumerate(mobile_cards[:5]):
            h = card.get_attribute("handle") or f"card-{i+1}"
            v = card.get_attribute("data-vendor") or "Unknown"
            p_el = card.query_selector("price-list")
            p_text = p_el.inner_text().replace("\n", " ").strip() if p_el else ""
            print(f"  Mobile [{i+1}] {h} ({v}): {p_text}")

        browser.close()

        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY:")
        print(f"- No 'FROM RS. 9,497' bug present: {no_old_from_price}")
        print(f"- Filtered matching price >= 15,000 displayed: {matching_price_found}")
        print(f"- Screenshots generated in: {OUTPUT_DIR}")
        print("=" * 80)

if __name__ == "__main__":
    run_verification()
