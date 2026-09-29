import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"

def test_add_to_cart():
    print("=" * 80)
    print("TESTING ADD TO CART WITH SELECTED COLOR VARIANT")
    print("=" * 80)

    url = "https://therareavenue.com/products/mini-rowan-crossbody-bag"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        print(f"Opening {url}...")
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Select "Gold/Pink"
        print("Selecting 'Gold/Pink' swatch...")
        swatch = page.locator("label:has-text('Gold/Pink'), [data-tooltip*='Gold/Pink']").first
        swatch.scroll_into_view_if_needed()
        swatch.click()
        page.wait_for_timeout(2000)
        
        selected_var_id = page.evaluate("() => document.querySelector('form[action*=\"/cart/add\"] input[name=\"id\"]').value")
        print(f"Selected variant ID in form: {selected_var_id}")
        
        # Click Add to cart
        atc_btn = page.locator("button[name='add'], .product-form__submit, buy-buttons button").first
        print(f"ATC Button text: '{atc_btn.inner_text().strip()}', disabled: {atc_btn.is_disabled()}")
        assert not atc_btn.is_disabled(), "ATC Button is disabled!"
        
        print("Clicking ADD TO CART...")
        atc_btn.click()
        page.wait_for_timeout(4000)
        
        # Check cart drawer or cart notification
        cart_shot = os.path.join(ARTIFACTS_DIR, "verified_atc_cart_drawer.png")
        page.screenshot(path=cart_shot)
        
        cart_info = page.evaluate("""() => {
            const drawer = document.querySelector('cart-drawer, #cart-drawer, .cart-drawer');
            const items = drawer ? Array.from(drawer.querySelectorAll('.line-item, .cart-item, [data-line-item]')) : [];
            const titles = items.map(it => it.innerText.replace(/\\s+/g, ' ').trim());
            return {
                drawerVisible: drawer ? !drawer.hasAttribute('hidden') && drawer.getAttribute('aria-hidden') !== 'true' : false,
                itemCount: items.length,
                firstItemText: titles[0] || 'NONE'
            };
        }""")
        print("Cart Drawer State:", cart_info)
        print(f"Saved cart screenshot to: {cart_shot}")
        
        browser.close()
        return cart_info

if __name__ == "__main__":
    test_add_to_cart()
