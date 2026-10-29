from playwright.sync_api import sync_playwright

URL = "https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI&filter.v.price.gte=15000&filter.v.price.lte=31560"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    # Find the card with swatches
    card = page.query_selector("product-card[handle='hana-medium-tote-bag-black-croc']")
    if not card:
        # find any card with swatches
        for c in page.query_selector_all("product-card"):
            if len(c.query_selector_all(".color-swatch")) >= 2:
                card = c
                break

    assert card is not None, "No card found!"
    card.scroll_into_view_if_needed()
    price_el = card.query_selector("price-list")
    initial_price = price_el.inner_text().strip()
    print("Initial price:", initial_price)

    swatches = card.query_selector_all(".color-swatch")
    swatch_2 = swatches[1]
    swatch_2.hover()
    page.wait_for_timeout(500)

    hovered_price = price_el.inner_text().strip()
    print("Hovered price:", hovered_price)

    # Now move mouse away to body / 0, 0
    page.mouse.move(0, 0)
    page.wait_for_timeout(500)

    restored_price = price_el.inner_text().strip()
    print("Restored price:", restored_price)

    browser.close()

    if restored_price == initial_price:
        print("SUCCESS: Price restored successfully on pointerleave!")
    else:
        print(f"FAILURE: Price was NOT restored! Expected '{initial_price}', got '{restored_price}'")
