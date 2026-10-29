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
        const fieldset = card.querySelector(".product-card__info fieldset");

        // Add direct listener to fieldset
        let fieldsetLeaveFired = false;
        fieldset.addEventListener("pointerleave", () => {
            fieldsetLeaveFired = true;
            // simulate restore
            if (priceList.dataset.selectedPriceHtml) {
                priceList.innerHTML = priceList.dataset.selectedPriceHtml;
            } else if (priceList.dataset.originalHtml) {
                priceList.innerHTML = priceList.dataset.originalHtml;
            }
        });

        // Hover swatch 2
        swatches[1].dispatchEvent(new PointerEvent("pointerover", { bubbles: true }));
        const priceAfterHover = priceList.innerText.trim();

        // Dispatch pointerleave on fieldset
        fieldset.dispatchEvent(new PointerEvent("pointerleave", { bubbles: false }));
        const priceAfterFieldsetLeave = priceList.innerText.trim();

        return {
            priceAfterHover,
            fieldsetLeaveFired,
            priceAfterFieldsetLeave
        };
    }''')
    print("Direct listener result:", res)
    browser.close()
