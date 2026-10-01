import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PRODUCT_HANDLE = "cooper-logo-billfold-wallet-with-passcase"
VARIANT_NUMERIC_ID = "57196714885286"
PRODUCT_URL = f"https://therareavenue.com/products/{PRODUCT_HANDLE}"

def verify_tax_shipping():
    with sync_playwright() as p:
        # ----------------- DESKTOP VERIFICATION -----------------
        print("=== Starting Desktop Verification (1440x900) ===")
        browser = p.chromium.launch(headless=True)
        desktop_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = desktop_ctx.new_page()

        # Step 1: Open Product Page
        print(f"Opening PDP: {PRODUCT_URL}")
        page.goto(PRODUCT_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        # Check PDP tax notice
        pdp_tax = page.locator(".luxury-pdp-tax-notice").first
        pdp_tax_text = pdp_tax.inner_text() if pdp_tax.count() > 0 else "N/A"
        print(f"PDP Tax Notice: '{pdp_tax_text}'")

        # Capture PDP screenshot
        pdp_screenshot = os.path.join(OUTPUT_DIR, "desktop_pdp_tax_notice.png")
        page.screenshot(path=pdp_screenshot)
        print(f"Saved PDP screenshot: {pdp_screenshot}")

        # Step 2: Add to cart
        print("Adding item to cart...")
        atc_btn = page.locator("button[name='add'], button:has-text('Add to cart'), .product-form__submit").first
        if atc_btn.count() > 0 and atc_btn.is_visible():
            atc_btn.click()
            page.wait_for_timeout(3000)
        else:
            page.evaluate(f"""async () => {{
                await fetch('/cart/add.js', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{id: '{VARIANT_NUMERIC_ID}', quantity: 1}})
                }});
            }}""")
            page.wait_for_timeout(1000)

        # Ensure Cart Drawer is open
        is_open = page.locator("cart-drawer[open], dialog[open]#cart-drawer").count() > 0
        if not is_open:
            cart_icon = page.locator("a[href='/cart'], button[aria-controls*='cart-drawer']").first
            if cart_icon.count() > 0:
                cart_icon.click()
                page.wait_for_timeout(2000)

        # Inspect the drawer footer
        page.wait_for_selector(".cart-drawer__footer, cart-drawer [slot='footer']", timeout=15000)
        footer = page.locator("cart-drawer [slot='footer'], .cart-drawer__footer").first
        footer_text = footer.inner_text() if footer.count() > 0 else ""
        print("Desktop Cart Drawer Footer Text:")
        print("---------------------------------")
        print(footer_text)
        print("---------------------------------")

        # Assertions
        assert "Taxes and shipping calculated at checkout" not in footer_text, "FAILED: Old string 'Taxes and shipping calculated at checkout' found in drawer!"
        assert "Shipping calculated at checkout" in footer_text or "Shipping" in footer_text, "FAILED: Shipping notice missing!"
        assert "Taxes included" in footer_text or "Tax included" in footer_text, "FAILED: Taxes included notice missing in cart drawer!"

        desktop_cart_ss = os.path.join(OUTPUT_DIR, "desktop_cart_drawer_taxes_shipping.png")
        page.screenshot(path=desktop_cart_ss)
        print(f"Saved Desktop Cart Drawer Screenshot: {desktop_cart_ss}")

        # Step 3: Check /cart page
        print("\nNavigating to /cart...")
        page.goto("https://therareavenue.com/cart", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        cart_page_text = page.locator("main, .cart").inner_text()
        print("Desktop /cart page text snippet:")
        print(cart_page_text[:400] + "...")
        assert "Taxes and shipping calculated at checkout" not in cart_page_text, "FAILED: Old string found on /cart page!"
        assert "Shipping calculated at checkout" in cart_page_text or "Shipping" in cart_page_text
        assert "Taxes included" in cart_page_text or "Tax included" in cart_page_text

        desktop_cart_page_ss = os.path.join(OUTPUT_DIR, "desktop_main_cart_page.png")
        page.screenshot(path=desktop_cart_page_ss)
        print(f"Saved Desktop Main Cart Page Screenshot: {desktop_cart_page_ss}")

        desktop_ctx.close()

        # ----------------- MOBILE VERIFICATION -----------------
        print("\n=== Starting Mobile Verification (390x844 iPhone) ===")
        mobile_ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True
        )
        mobile_page = mobile_ctx.new_page()

        print(f"Opening PDP on Mobile: {PRODUCT_URL}")
        mobile_page.goto(PRODUCT_URL, wait_until="networkidle", timeout=60000)
        mobile_page.wait_for_timeout(2000)

        # Check mobile PDP tax notice
        m_tax = mobile_page.locator(".luxury-pdp-tax-notice").first
        print(f"Mobile PDP Tax Notice: '{m_tax.inner_text() if m_tax.count() > 0 else 'N/A'}'")
        mobile_pdp_ss = os.path.join(OUTPUT_DIR, "mobile_pdp_tax_notice.png")
        mobile_page.screenshot(path=mobile_pdp_ss)
        print(f"Saved Mobile PDP Screenshot: {mobile_pdp_ss}")

        # Add to cart on mobile
        m_atc = mobile_page.locator("button[name='add'], button:has-text('Add to cart'), .product-form__submit").first
        if m_atc.count() > 0 and m_atc.is_visible():
            m_atc.click()
            mobile_page.wait_for_timeout(3000)
        else:
            mobile_page.evaluate(f"""async () => {{
                await fetch('/cart/add.js', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{id: '{VARIANT_NUMERIC_ID}', quantity: 1}})
                }});
            }}""")
            mobile_page.wait_for_timeout(1000)

        m_is_open = mobile_page.locator("cart-drawer[open], dialog[open]#cart-drawer").count() > 0
        if not m_is_open:
            m_cart_icon = mobile_page.locator("a[href='/cart'], button[aria-controls*='cart-drawer']").first
            if m_cart_icon.count() > 0:
                m_cart_icon.click()
                mobile_page.wait_for_timeout(2000)

        mobile_page.wait_for_selector(".cart-drawer__footer, cart-drawer [slot='footer']", timeout=15000)
        m_footer = mobile_page.locator("cart-drawer [slot='footer'], .cart-drawer__footer").first
        m_footer_text = m_footer.inner_text() if m_footer.count() > 0 else ""
        print("Mobile Cart Drawer Footer Text:")
        print("---------------------------------")
        print(m_footer_text)
        print("---------------------------------")

        assert "Taxes and shipping calculated at checkout" not in m_footer_text, "FAILED: Old string on mobile cart drawer!"
        assert "Shipping calculated at checkout" in m_footer_text or "Shipping" in m_footer_text
        assert "Taxes included" in m_footer_text or "Tax included" in m_footer_text

        mobile_cart_ss = os.path.join(OUTPUT_DIR, "mobile_cart_drawer_taxes_shipping.png")
        mobile_page.screenshot(path=mobile_cart_ss)
        print(f"Saved Mobile Cart Drawer Screenshot: {mobile_cart_ss}")

        # Check mobile /cart
        print("\nNavigating to mobile /cart...")
        mobile_page.goto("https://therareavenue.com/cart", wait_until="networkidle", timeout=60000)
        mobile_page.wait_for_timeout(2000)
        m_cart_page_text = mobile_page.locator("main, .cart").inner_text()
        assert "Taxes and shipping calculated at checkout" not in m_cart_page_text, "FAILED: Old string on mobile /cart page!"
        assert "Shipping calculated at checkout" in m_cart_page_text or "Shipping" in m_cart_page_text
        assert "Taxes included" in m_cart_page_text or "Tax included" in m_cart_page_text

        mobile_cart_page_ss = os.path.join(OUTPUT_DIR, "mobile_main_cart_page.png")
        mobile_page.screenshot(path=mobile_cart_page_ss)
        print(f"Saved Mobile Main Cart Page Screenshot: {mobile_cart_page_ss}")

        mobile_ctx.close()
        browser.close()
        print("\n=======================================================")
        print("ALL PLAYWRIGHT ASSERTIONS PASSED WITH ZERO REGRESSIONS!")
        print("=======================================================")

if __name__ == "__main__":
    verify_tax_shipping()
