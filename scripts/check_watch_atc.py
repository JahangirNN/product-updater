from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://therareavenue.com/products/versace-hellenyium-automatic-green-dial-mens-watch-veqca0124', wait_until='domcontentloaded')
    data = page.evaluate("""() => {
        const btn = document.querySelector('button[name="add"], .product-form__submit, buy-buttons button');
        return {
            btnText: btn ? btn.innerText.trim() : 'NONE',
            btnDisabled: btn ? btn.disabled : null
        };
    }""")
    print("Watch product:", data)
    browser.close()
