import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

ADDITIONAL_TESTS = [
    {
        "handle": "teri-mini-crossbody-bag-in-signature-denim",
        "name": "Coach Teri Mini Crossbody In Denim",
        "variants_to_test": ["Gold/Walnut/Black", "Silver/Light Sand"]
    },
    {
        "handle": "teri-shoulder-bag",
        "name": "Coach Teri Shoulder Bag",
        "variants_to_test": ["Gold/Carnation", "Gold/Deep Blue"]
    },
    {
        "handle": "piper-flex-logo-stitched-suede-bootie",
        "name": "Michael Kors Piper Flex Bootie",
        "variants_to_test": ["Luggage", "Black"]
    }
]

def run_additional_verification():
    print("=" * 80)
    print("RUNNING ADDITIONAL PDP VERIFICATION ACROSS COACH & MICHAEL KORS")
    print("=" * 80)

    summary = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        for prod in ADDITIONAL_TESTS:
            handle = prod["handle"]
            name = prod["name"]
            url = f"https://therareavenue.com/products/{handle}"
            print(f"\n>>> TESTING: {name} ({url})")

            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)

            init_shot = os.path.join(ARTIFACTS_DIR, f"verified_{handle}_0_initial.png")
            page.screenshot(path=init_shot, full_page=False)

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
            print(f"  [Initial] Price: {init_info['price']} | Var ID: {init_info['variantId']}")
            print(f"  [Initial] Image: {init_info['imgSrc'][:70]}...")

            current_var_id = init_info["variantId"]

            for v_idx, swatch_name in enumerate(prod["variants_to_test"], 1):
                print(f"  -> Selecting variant: '{swatch_name}'...")
                swatch = page.locator(f"label:has-text('{swatch_name}'), label[data-tooltip*='{swatch_name}'], [aria-label*='{swatch_name}']").first
                if swatch.count() == 0:
                    swatch = page.locator(f"label:text-matches('{swatch_name}', 'i')").first

                if swatch.count() == 0:
                    print(f"     FAILED: swatch '{swatch_name}' not found")
                    continue

                swatch.scroll_into_view_if_needed()
                swatch.click()
                page.wait_for_timeout(2500)

                shot_path = os.path.join(ARTIFACTS_DIR, f"verified_{handle}_{v_idx}_{swatch_name.replace('/', '_').replace(' ', '_')}.png")
                page.screenshot(path=shot_path, full_page=False)

                v_state = page.evaluate("""() => {
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

                id_changed = (v_state["variantId"] != current_var_id)
                img_changed = (v_state["imgSrc"] != init_info["imgSrc"])
                has_rupees = "RS." in v_state["price"].upper()

                print(f"     Price: {v_state['price']} (Whole-rupee: {has_rupees})")
                print(f"     Var ID: {v_state['variantId']} (Changed: {id_changed})")
                print(f"     Active Img: {v_state['imgSrc'][:70]}...")

                passed = id_changed and img_changed and has_rupees
                status = "PASS" if passed else "FAIL"
                print(f"     >>> STATUS: [{status}]")
                summary.append({"prod": name, "variant": swatch_name, "status": status})
                current_var_id = v_state["variantId"]

        browser.close()

    print("\n" + "=" * 80)
    print("ADDITIONAL VERIFICATION AUDIT TABLE:")
    print("=" * 80)
    for s in summary:
        print(f"[{s['status']}] {s['prod']:35} | {s['variant']}")
    print("=" * 80)

if __name__ == "__main__":
    run_additional_verification()
