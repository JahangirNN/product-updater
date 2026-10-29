import sys
import os
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Verify /collections/ready-to-ship
        print("Navigating to https://therareavenue.com/collections/ready-to-ship...")
        page.goto("https://therareavenue.com/collections/ready-to-ship", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Count cards and badges
        cards = page.locator(".product-card")
        card_count = cards.count()
        badges = page.locator(".badge--ready-to-ship")
        badge_count = badges.count()
        print(f"Found {card_count} product cards and {badge_count} 'Ready to Ship' badges on /collections/ready-to-ship")

        screenshot_path_1 = os.path.join(OUTPUT_DIR, "ready_to_ship_collection.png")
        page.screenshot(path=screenshot_path_1, full_page=False)
        print(f"Saved screenshot: {screenshot_path_1}")

        # 2. Verify /collections/michael-kors
        print("\nNavigating to https://therareavenue.com/collections/michael-kors...")
        page.goto("https://therareavenue.com/collections/michael-kors", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        mk_cards = page.locator(".product-card")
        mk_card_count = mk_cards.count()
        mk_badges = page.locator(".badge--ready-to-ship")
        mk_badge_count = mk_badges.count()
        print(f"Found {mk_card_count} product cards and {mk_badge_count} 'Ready to Ship' badges on /collections/michael-kors")

        screenshot_path_2 = os.path.join(OUTPUT_DIR, "michael_kors_showroom_badges.png")
        page.screenshot(path=screenshot_path_2, full_page=False)
        print(f"Saved screenshot: {screenshot_path_2}")

        # 3. Verify /collections/mens-bags with Michael Kors
        print("\nNavigating to https://therareavenue.com/collections/mens-bags...")
        page.goto("https://therareavenue.com/collections/mens-bags", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        mb_cards = page.locator(".product-card")
        mb_card_count = mb_cards.count()
        mb_badges = page.locator(".badge--ready-to-ship")
        mb_badge_count = mb_badges.count()
        print(f"Found {mb_card_count} product cards and {mb_badge_count} 'Ready to Ship' badges on /collections/mens-bags")

        screenshot_path_3 = os.path.join(OUTPUT_DIR, "mens_bags_badges.png")
        page.screenshot(path=screenshot_path_3, full_page=False)
        print(f"Saved screenshot: {screenshot_path_3}")

        # 4. Verify MK Product Page (PDP)
        first_card = page.locator(".product-card").first
        if first_card.count() > 0:
            link = first_card.locator("a.product-card__media").get_attribute("href")
            if link:
                pdp_url = f"https://therareavenue.com{link}" if link.startswith("/") else link
                print(f"\nNavigating to PDP: {pdp_url}...")
                page.goto(pdp_url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(2000)
                pdp_badges = page.locator(".badge--ready-to-ship")
                print(f"PDP 'Ready to Ship' badges: {pdp_badges.count()}")

                screenshot_path_4 = os.path.join(OUTPUT_DIR, "michael_kors_pdp_badge.png")
                page.screenshot(path=screenshot_path_4, full_page=False)
                print(f"Saved screenshot: {screenshot_path_4}")

        browser.close()
        print("\nPlaywright verification complete!")

if __name__ == "__main__":
    run_verification()
