import os
import sys
from playwright.sync_api import sync_playwright

url = "https://therareavenue.com/collections/women"
artifacts_dir = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    
    print(f"Navigating to {url}...")
    resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
    print(f"HTTP Status: {resp.status}")
    page.wait_for_timeout(3000)
    
    info = page.evaluate("""() => {
        const titleEl = document.querySelector('h1, .collection-banner__title, .collection-title');
        const countEl = document.querySelector('.facets__total-products, .facets__product-count, .product-count');
        const cards = document.querySelectorAll('product-card, .product-card, .product-item, .grid-product');
        return {
            title: titleEl ? titleEl.innerText.trim() : '',
            countText: countEl ? countEl.innerText.trim() : '',
            renderedCardsCount: cards.length
        };
    }""")
    
    print(f"Storefront Page Title: {info['title']}")
    print(f"Storefront Count Text: {info['countText']}")
    print(f"Rendered Product Cards on 1st page: {info['renderedCardsCount']}")
    
    shot_path = os.path.join(artifacts_dir, "womens_edit_collection_live.png")
    page.screenshot(path=shot_path, full_page=False)
    print(f"Saved live screenshot to: {shot_path}")
    
    browser.close()
