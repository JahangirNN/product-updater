import os
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "live_audit")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    print("Navigating desktop to https://therareavenue.com/ ...")
    page.goto("https://therareavenue.com/", wait_until="commit", timeout=60000)
    page.wait_for_selector("body", timeout=30000)
    time.sleep(4)
    
    # Hide any lingering popups or overlays
    page.add_style_tag(content="""
        dialog, [id*='popup'], [class*='popup'], [class*='newsletter-modal'], [class*='overlay-group'], .newsletter-popup, [id*='newsletter-modal'] {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }
    """)

    # Smoothly scroll to bottom to hydrate all reveal animations & lazy-loaded media
    print("Hydrating scroll triggers and media...")
    total_height = page.evaluate("document.body.scrollHeight")
    for y in range(0, total_height, 700):
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(0.12)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(1.5)

    # Capture individual sections
    sections = page.locator("[id^='shopify-section-template--']").all()
    print(f"Found {len(sections)} template sections.")
    for i, sec in enumerate(sections, 1):
        sec_id = sec.get_attribute("id") or f"section_{i}"
        clean_id = sec_id.replace("shopify-section-template--", "").replace("__", "_")
        sec_path = os.path.join(OUTPUT_DIR, f"{i:02d}_{clean_id}.png")
        try:
            # Scroll section into view before screenshotting
            sec.scroll_into_view_if_needed()
            time.sleep(0.2)
            sec.screenshot(path=sec_path)
            print(f"Captured {clean_id}: {sec_path}")
        except Exception as e:
            print(f"Could not screenshot {clean_id}: {e}")

    # Capture full page desktop
    full_path = os.path.join(OUTPUT_DIR, "live_full_desktop.png")
    page.screenshot(path=full_path, full_page=True)
    print(f"Captured full desktop page: {full_path}")

    # Also capture mobile viewport
    print("Navigating mobile (390px)...")
    mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
    mobile_page.goto("https://therareavenue.com/", wait_until="commit", timeout=60000)
    mobile_page.wait_for_selector("body", timeout=30000)
    time.sleep(3)
    mobile_page.add_style_tag(content="""
        dialog, [id*='popup'], [class*='popup'], [class*='newsletter-modal'], [class*='overlay-group'], .newsletter-popup, [id*='newsletter-modal'] {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }
    """)
    m_height = mobile_page.evaluate("document.body.scrollHeight")
    for y in range(0, m_height, 700):
        mobile_page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(0.1)
    mobile_page.evaluate("window.scrollTo(0, 0)")
    time.sleep(1)

    mobile_path = os.path.join(OUTPUT_DIR, "live_full_mobile.png")
    mobile_page.screenshot(path=mobile_path, full_page=True)
    print(f"Captured mobile: {mobile_path}")

    browser.close()

print("Audit screenshots complete!")
