from playwright.sync_api import sync_playwright

URL = "https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI&filter.v.price.gte=15000&filter.v.price.lte=31560"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    # Let's inspect in page.evaluate
    res = page.evaluate('''() => {
        const card = document.querySelector("product-card[handle='hana-medium-tote-bag-black-croc']");
        const fieldset = card.querySelector(".product-card__info fieldset");
        const priceList = card.querySelector("price-list");
        
        let pointerleaveFired = false;
        fieldset.addEventListener("pointerleave", () => {
            pointerleaveFired = true;
        });

        // Let's check delegate3 listeners or test dispatchEvent
        const event = new PointerEvent("pointerleave", { bubbles: false, cancelable: true });
        fieldset.dispatchEvent(event);

        return {
            pointerleaveFired,
            originalHtml: priceList.dataset.originalHtml,
            priceListHtml: priceList.innerHTML
        };
    }''')
    print("Direct dispatch result:", res)
    browser.close()
