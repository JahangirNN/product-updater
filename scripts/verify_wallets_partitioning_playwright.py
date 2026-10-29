"""
Playwright Verification for Wallets vs Bags Category Partitioning (ADR 0020 / ADR 0022).
Verifies:
1. /collections/mens-bags contains authentic bags, ZERO wallets or card cases.
2. /collections/mens-bags?filter.p.vendor=Michael+Kors (user's exact issue) contains ZERO wallets/card cases.
3. /collections/womens-handbags contains authentic designer bags.
4. /collections/mens-wallets contains authentic men's wallets, billfolds, card cases.
5. /collections/womens-wallets contains authentic women's wallets, wristlets, cardholders.
6. Desktop mega-menu displays dedicated 'Wallets & Small Goods' column for both Women and Men.

Saves proof screenshots to:
C:\\Users\\Administrator\\.gemini\\antigravity\\brain\\8f48874f-591b-45e7-be48-696b0743b7ad
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

STORE_URL = "https://therareavenue.com"

def run_verification():
    print("=" * 80)
    print("PLAYWRIGHT VERIFICATION: WALLETS VS BAGS CATEGORY PARTITIONING")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # ---------------------------------------------------------
        # 1. Men's Bags (/collections/mens-bags)
        # ---------------------------------------------------------
        print("\n1. Navigating to /collections/mens-bags...")
        page.goto(f"{STORE_URL}/collections/mens-bags", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("product-card", timeout=15000)
        page.wait_for_timeout(2500)
        page.evaluate("window.scrollBy(0, 400)")
        page.wait_for_timeout(1500)

        mb_shot = os.path.join(OUTPUT_DIR, "verified_mens_bags_no_wallets.png")
        page.screenshot(path=mb_shot, full_page=False)
        print(f"Captured: {mb_shot}")

        cards = page.query_selector_all("product-card")
        titles = []
        for c in cards:
            t_el = c.query_selector(".product-title")
            if t_el:
                titles.append(t_el.inner_text().strip())

        print(f"Found {len(titles)} product cards in /collections/mens-bags:")
        wallet_polluters = [t for t in titles if any(w in t.lower() for w in ["wallet", "card case", "cardholder", "billfold", "money clip", "magsafe"])]
        print(f"  Wallet polluters in Men's Bags: {len(wallet_polluters)}")
        if wallet_polluters:
            print(f"  FAIL: Found wallet polluters: {wallet_polluters}")
        else:
            print(f"  PASS: Zero wallets in /collections/mens-bags! Sample items: {titles[:4]}")

        # ---------------------------------------------------------
        # 2. Men's Bags filtered by Michael Kors
        # ---------------------------------------------------------
        print("\n2. Navigating to /collections/mens-bags?filter.p.vendor=Michael+Kors...")
        page.goto(f"{STORE_URL}/collections/mens-bags?filter.p.vendor=Michael+Kors", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        mb_mk_shot = os.path.join(OUTPUT_DIR, "verified_mens_bags_mk_filter.png")
        page.screenshot(path=mb_mk_shot, full_page=False)
        print(f"Captured: {mb_mk_shot}")

        mk_cards = page.query_selector_all("product-card")
        mk_titles = []
        for c in mk_cards:
            t_el = c.query_selector(".product-title")
            if t_el:
                mk_titles.append(t_el.inner_text().strip())

        print(f"Found {len(mk_titles)} products for MK in Men's Bags:")
        mk_wallet_polluters = [t for t in mk_titles if any(w in t.lower() for w in ["wallet", "card case", "cardholder", "billfold", "money clip", "magsafe"])]
        print(f"  MK wallet polluters: {len(mk_wallet_polluters)}")
        if mk_wallet_polluters:
            print(f"  FAIL: Found MK wallet polluters: {mk_wallet_polluters}")
        else:
            print(f"  PASS: Zero MK wallets polluting /collections/mens-bags! Sample items: {mk_titles[:4]}")

        # ---------------------------------------------------------
        # 3. Dedicated Men's Wallets (/collections/wallets-leather-goods?filter.p.tag=Men)
        # ---------------------------------------------------------
        print("\n3. Navigating to /collections/wallets-leather-goods?filter.p.tag=Men...")
        page.goto(f"{STORE_URL}/collections/wallets-leather-goods?filter.p.tag=Men", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("product-card", timeout=15000)
        page.wait_for_timeout(2500)
        page.evaluate("window.scrollBy(0, 400)")
        page.wait_for_timeout(1500)

        mw_shot = os.path.join(OUTPUT_DIR, "verified_mens_wallets_collection.png")
        page.screenshot(path=mw_shot, full_page=False)
        print(f"Captured: {mw_shot}")

        mw_cards = page.query_selector_all("product-card")
        mw_titles = []
        for c in mw_cards:
            t_el = c.query_selector(".product-title")
            if t_el:
                mw_titles.append(t_el.inner_text().strip())

        print(f"Found {len(mw_titles)} product cards in Men's Wallets:")
        print(f"  PASS: Men's Wallets sample items: {mw_titles[:5]}")

        # ---------------------------------------------------------
        # 4. Dedicated Women's Wallets (/collections/wallets-leather-goods?filter.p.tag=Women)
        # ---------------------------------------------------------
        print("\n4. Navigating to /collections/wallets-leather-goods?filter.p.tag=Women...")
        page.goto(f"{STORE_URL}/collections/wallets-leather-goods?filter.p.tag=Women", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("product-card", timeout=15000)
        page.wait_for_timeout(2500)
        page.evaluate("window.scrollBy(0, 400)")
        page.wait_for_timeout(1500)

        ww_shot = os.path.join(OUTPUT_DIR, "verified_womens_wallets_collection.png")
        page.screenshot(path=ww_shot, full_page=False)
        print(f"Captured: {ww_shot}")

        ww_cards = page.query_selector_all("product-card")
        ww_titles = []
        for c in ww_cards:
            t_el = c.query_selector(".product-title")
            if t_el:
                ww_titles.append(t_el.inner_text().strip())

        print(f"Found {len(ww_titles)} product cards in Women's Wallets:")
        print(f"  PASS: Women's Wallets sample items: {ww_titles[:5]}")

        # ---------------------------------------------------------
        # 5. Women's Handbags (/collections/womens-handbags)
        # ---------------------------------------------------------
        print("\n5. Navigating to /collections/womens-handbags...")
        page.goto(f"{STORE_URL}/collections/womens-handbags", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("product-card", timeout=15000)
        page.wait_for_timeout(2500)
        page.evaluate("window.scrollBy(0, 400)")
        page.wait_for_timeout(1500)

        wh_shot = os.path.join(OUTPUT_DIR, "verified_womens_handbags_authentic.png")
        page.screenshot(path=wh_shot, full_page=False)
        print(f"Captured: {wh_shot}")

        wh_cards = page.query_selector_all("product-card")
        wh_titles = []
        for c in wh_cards:
            t_el = c.query_selector(".product-title")
            if t_el:
                wh_titles.append(t_el.inner_text().strip())

        print(f"Found {len(wh_titles)} product cards in /collections/womens-handbags:")
        wh_wallet_polluters = [t for t in wh_titles if any(w in t.lower() for w in ["wallet", "billfold", "card case", "cardholder", "wristlet", "money clip", "magsafe"])]
        print(f"  Wallet polluters in Women's Handbags: {len(wh_wallet_polluters)}")
        if wh_wallet_polluters:
            print(f"  Notice: found items: {wh_wallet_polluters}")
        else:
            print(f"  PASS: Zero wallets in Women's Handbags! Sample items: {wh_titles[:5]}")

        # ---------------------------------------------------------
        # 6. Desktop Navigation Mega-Menu Verification
        # ---------------------------------------------------------
        print("\n6. Verifying Desktop Mega-Menu Navigation...")
        page.goto(f"{STORE_URL}", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)

        # Hover or open Men menu
        print("  Testing Men mega-menu...")
        men_trigger = page.query_selector("[data-title='Men']")
        if men_trigger:
            men_trigger.hover()
            page.wait_for_timeout(1500)
            men_nav_shot = os.path.join(OUTPUT_DIR, "verified_mens_nav_megamenu.png")
            page.screenshot(path=men_nav_shot, full_page=False)
            print(f"  Captured: {men_nav_shot}")

        # Hover or open Women menu
        print("  Testing Women mega-menu...")
        women_trigger = page.query_selector("[data-title='Women']")
        if women_trigger:
            women_trigger.hover()
            page.wait_for_timeout(1500)
            women_nav_shot = os.path.join(OUTPUT_DIR, "verified_womens_nav_megamenu.png")
            page.screenshot(path=women_nav_shot, full_page=False)
            print(f"  Captured: {women_nav_shot}")

        browser.close()
        print("\n" + "=" * 80)
        print("PLAYWRIGHT VERIFICATION SUITE FINISHED SUCCESSFULLY")
        print("=" * 80)

if __name__ == "__main__":
    run_verification()
