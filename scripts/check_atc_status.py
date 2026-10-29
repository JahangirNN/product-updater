import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    for handle in ["hana-large-tote-bag-pink", "nell-fringe-hardware-top-handle-bag-burgundy", "mini-rowan-crossbody-bag"]:
        page.goto(f"https://therareavenue.com/products/{handle}", wait_until="domcontentloaded")
        data = page.evaluate("""() => {
            const btn = document.querySelector('button[name="add"], .product-form__submit, buy-buttons button');
            const swatch = document.querySelector('.color-swatch, .block-swatch');
            return {
                btnText: btn ? btn.innerText.trim() : 'NONE',
                btnDisabled: btn ? btn.disabled : null,
                swatchClass: swatch ? swatch.className : 'NONE'
            };
        }""")
        print(f"{handle}:", data)
    browser.close()
