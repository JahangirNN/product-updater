from playwright.sync_api import sync_playwright
import os

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto("https://therareavenue.com", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    men_el = page.locator("[data-title='Men']").first
    men_el.hover()
    page.wait_for_timeout(1500)
    shot = os.path.join(OUTPUT_DIR, "verified_desktop_men_nav.png")
    page.screenshot(path=shot, full_page=False)
    print("Men nav screenshot saved!")
    b.close()
