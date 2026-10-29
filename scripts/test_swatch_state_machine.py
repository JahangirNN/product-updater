from playwright.sync_api import sync_playwright

URL = "https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI&filter.v.price.gte=15000&filter.v.price.lte=31560"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    card = page.query_selector("product-card[handle='hana-medium-tote-bag-black-croc']")
    assert card is not None, "No card found!"
    card.scroll_into_view_if_needed()
    price_el = card.query_selector("price-list")
    initial_price = price_el.inner_text().strip()
    print("1. Initial price:", initial_price)

    swatches = card.query_selector_all(".color-swatch")
    swatch_2 = swatches[1]
    
    # Click Swatch 2
    swatch_2.click()
    page.wait_for_timeout(500)
    clicked_price = price_el.inner_text().strip()
    print("2. Price after click Swatch 2:", clicked_price)

    # Hover Swatch 20 (Dark Chocolate Brown, Rs 21,999)
    swatch_20 = swatches[19]
    swatch_20.hover()
    page.wait_for_timeout(500)
    hover_20_price = price_el.inner_text().strip()
    print("3. Price after hover Swatch 20:", hover_20_price)

    # Move mouse away to 0, 0
    page.mouse.move(0, 0)
    page.wait_for_timeout(500)
    restored_after_click_price = price_el.inner_text().strip()
    print("4. Price after mouse leaves:", restored_after_click_price)

    browser.close()

    assert "13,353" in clicked_price, f"Clicked price wrong: {clicked_price}"
    assert "21,999" in hover_20_price, f"Hover 20 price wrong: {hover_20_price}"
    assert "13,353" in restored_after_click_price, f"Restored price should be clicked price (13,353), got: {restored_after_click_price}"
    print("SUCCESS: State machine transition verified! Hover -> Click -> Hover other -> Leave restores to clicked!")
