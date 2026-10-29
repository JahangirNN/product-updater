from playwright.sync_api import sync_playwright

URL = "https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI&filter.v.price.gte=15000&filter.v.price.lte=31560"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    res = page.evaluate('''() => {
        const card = document.querySelector("product-card[handle='hana-medium-tote-bag-black-croc']");
        const swatches = card.querySelectorAll(".color-swatch");
        const priceList = card.querySelector("price-list");

        // Hover swatch 2
        swatches[1].dispatchEvent(new PointerEvent("pointerover", { bubbles: true }));
        const priceAfterHover = priceList.innerText.trim();

        // Dispatch pointerleave on fieldset with bubbles: false (native browser behavior)
        const fieldset = card.querySelector(".product-card__info fieldset");
        fieldset.dispatchEvent(new PointerEvent("pointerleave", { bubbles: false }));
        const priceAfterPointerleaveNoBubble = priceList.innerText.trim();

        // Dispatch pointerleave on card
        card.dispatchEvent(new PointerEvent("pointerleave", { bubbles: false }));
        const priceAfterPointerleaveOnCard = priceList.innerText.trim();

        return {
            priceAfterHover,
            priceAfterPointerleaveNoBubble,
            priceAfterPointerleaveOnCard
        };
    }''')
    print("Test result:", res)
    browser.close()
