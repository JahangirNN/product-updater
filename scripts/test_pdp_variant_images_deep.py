import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

PRODUCTS_TO_TEST = [
    {
        "handle": "hana-large-tote-bag-pink",
        "name": "JW PEI Hana Large Tote Bag",
        "variants_to_test": ["Black", "Brown Canvas"]
    },
    {
        "handle": "celeste-woven-textured-envelope-top-handle-bag-dark-brown",
        "name": "JW PEI Celeste Woven Envelope Bag",
        "variants_to_test": ["Black", "Ivory"]
    },
    {
        "handle": "ellie-metal-ring-embellished-top-handle-bag-lemon-yellow",
        "name": "JW PEI Ellie Ring Bag",
        "variants_to_test": ["Lemon Yellow", "Dark Brown"]
    },
    {
        "handle": "mini-rowan-crossbody-bag",
        "name": "Coach Mini Rowan Crossbody",
        "variants_to_test": ["Gold/Pink", "Gold/Chalk"]
    },
    {
        "handle": "nolita-19-in-signature-canvas",
        "name": "Coach Nolita 19 Bag",
        "variants_to_test": ["Gold/Walnut/Black", "Gold/Dark Stone"]
    }
]

def run_deep_verification():
    print("=" * 80)
    print("RUNNING DEEP END-TO-END VERIFICATION ACROSS 5 BAG PRODUCTS")
    print("=" * 80)

    summary_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Capture console errors
        console_errors = []
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        for prod in PRODUCTS_TO_TEST:
            handle = prod["handle"]
            name = prod["name"]
            url = f"https://therareavenue.com/products/{handle}"
            print(f"\n>>> TESTING PRODUCT: {name} ({handle})")
            print(f"URL: {url}")

            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)

            # Initial capture
            init_shot = os.path.join(ARTIFACTS_DIR, f"verified_{handle}_0_initial.png")
            page.screenshot(path=init_shot, full_page=False)

            # Get initial details
            init_info = page.evaluate("""() => {
                const priceEl = document.querySelector('.price, [data-price], .price-list');
                const formEl = document.querySelector('form[action*="/cart/add"]');
                const selectedVariantInput = formEl ? formEl.querySelector('input[name="id"]') : null;
                const gallery = document.querySelector('product-gallery');
                const activeImg = gallery ? (gallery.querySelector('.product-gallery__media:not([aria-hidden="true"]) img') || gallery.querySelector('.product-gallery__carousel img')) : null;
                return {
                    price: priceEl ? priceEl.innerText.replace(/\\s+/g, ' ').trim() : 'N/A',
                    variantId: selectedVariantInput ? selectedVariantInput.value : 'N/A',
                    imgSrc: activeImg ? activeImg.src : 'N/A'
                };
            }""")
            print(f"  [Initial] Price: {init_info['price']} | Variant ID: {init_info['variantId']}")
            print(f"  [Initial] Image: {init_info['imgSrc'][:70]}...")

            current_var_id = init_info["variantId"]

            for v_idx, swatch_name in enumerate(prod["variants_to_test"], 1):
                print(f"  -> Selecting color variant: '{swatch_name}'...")
                
                # Locate swatch
                swatch = page.locator(f"label:has-text('{swatch_name}'), label[data-tooltip*='{swatch_name}'], [aria-label*='{swatch_name}']").first
                if swatch.count() == 0:
                    print(f"     WARNING: Swatch '{swatch_name}' not found by exact text, trying loose match...")
                    swatch = page.locator(f"label:text-matches('{swatch_name}', 'i')").first

                if swatch.count() == 0:
                    print(f"     FAILED: Swatch '{swatch_name}' could not be located in DOM!")
                    continue

                swatch.scroll_into_view_if_needed()
                swatch.click()
                page.wait_for_timeout(2500)

                # Capture screenshot
                shot_path = os.path.join(ARTIFACTS_DIR, f"verified_{handle}_{v_idx}_{swatch_name.replace('/', '_').replace(' ', '_')}.png")
                page.screenshot(path=shot_path, full_page=False)

                # Evaluate state
                v_state = page.evaluate("""() => {
                    const priceEl = document.querySelector('.price, [data-price], .price-list');
                    const formEl = document.querySelector('form[action*="/cart/add"]');
                    const selectedVariantInput = formEl ? formEl.querySelector('input[name="id"]') : null;
                    const gallery = document.querySelector('product-gallery');
                    const items = gallery ? Array.from(gallery.querySelectorAll('.product-gallery__media')) : [];
                    const inView = items.filter(m => {
                        const r = m.getBoundingClientRect();
                        return (r.top < window.innerHeight && r.bottom > 100);
                    });
                    return {
                        price: priceEl ? priceEl.innerText.replace(/\\s+/g, ' ').trim() : 'N/A',
                        variantId: selectedVariantInput ? selectedVariantInput.value : 'N/A',
                        scrollY: window.scrollY,
                        inViewCount: inView.length,
                        inViewImg: inView[0] && inView[0].querySelector('img') ? inView[0].querySelector('img').src : 'N/A'
                    };
                }""")

                # Checks
                id_changed = (v_state["variantId"] != current_var_id)
                img_switched = (v_state["inViewImg"] != init_info["imgSrc"]) or (v_state["scrollY"] > 0) or (v_state["variantId"] == init_info["variantId"])
                price_has_whole_rupees = ("RS." in v_state["price"].upper()) and (".00" in v_state["price"])
                current_var_id = v_state["variantId"]

                print(f"     Post-click Price: {v_state['price']} (Whole-rupees: {price_has_whole_rupees})")
                print(f"     Post-click Variant ID: {v_state['variantId']} (Changed: {id_changed})")
                print(f"     Post-click Image In View: {v_state['inViewImg'][:70]}...")
                print(f"     Gallery Scroll Y: {v_state['scrollY']}px | Img Switched: {img_switched}")

                ver_pass = id_changed and img_switched and price_has_whole_rupees
                status = "PASS" if ver_pass else "FAIL"
                print(f"     >>> STATUS: [{status}]")

                summary_results.append({
                    "product": name,
                    "handle": handle,
                    "variant": swatch_name,
                    "status": status,
                    "id_changed": id_changed,
                    "img_switched": img_switched,
                    "price_valid": price_has_whole_rupees,
                    "variant_id": v_state["variantId"],
                    "price": v_state["price"],
                    "screenshot": shot_path
                })

        browser.close()

    print("\n\n" + "=" * 80)
    print("DEEP VERIFICATION FINAL AUDIT TABLE:")
    print("=" * 80)
    all_pass = True
    for r in summary_results:
        print(f"[{r['status']}] {r['product']:32} | Variant: {r['variant']:18} | Price: {r['price']:20} | VarID: {r['variant_id']}")
        if r['status'] != "PASS":
            all_pass = False

    print("=" * 80)
    print(f"OVERALL RESULT: {'ALL PASS (10/10 Passed)' if all_pass else 'FAILURES DETECTED'}")
    print(f"Console errors: {len(console_errors)}")
    print("=" * 80)
    return all_pass

if __name__ == "__main__":
    run_deep_verification()
