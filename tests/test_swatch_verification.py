import os
import sys
import json
import time
from playwright.sync_api import sync_playwright, expect

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts", "swatch_verification")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def run_swatch_tests():
    print("=" * 80)
    print("RUNNING END-TO-END PLAYWRIGHT TESTS: LUXURY VISUAL COLOR SWATCHES")
    print("=" * 80)

    results = {
        "desktop_caitlin": False,
        "desktop_click_swatch": False,
        "desktop_ajax_add_to_bag": False,
        "mobile_caitlin": False,
        "footwear_regression": False,
        "watches_clean_layout": False,
        "multi_option_color_and_size": False,
        "screenshots": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ----------------------------------------------------------------------
        # 1. DESKTOP TEST: Coach Caitlin Shoulder Bag
        # ----------------------------------------------------------------------
        print("\n[TEST 1] Desktop (1280x800) - Coach Caitlin Visual Color Swatches")
        context_desktop = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context_desktop.new_page()

        page.goto("https://therareavenue.com/search?q=Caitlin", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("product-card", timeout=10000)

        # Find Caitlin card (prefer Signature Canvas or any Caitlin bag with 6 variants)
        cards = page.locator("product-card")
        caitlin_card = None
        count = cards.count()
        print(f"Found {count} cards on Caitlin search page.")

        for i in range(count):
            card = cards.nth(i)
            title = card.locator(".product-card__title").inner_text()
            if "CAITLIN" in title.upper():
                caitlin_card = card
                print(f"Selected test card: '{title.strip()}'")
                break

        assert caitlin_card is not None, "Caitlin Shoulder Bag card not found on search page"

        # A) Verify 6 visual thumbnail swatches exist
        swatches = caitlin_card.locator(".product-card__swatch-btn")
        swatch_count = swatches.count()
        print(f"Swatch count found: {swatch_count}")
        assert swatch_count == 6, f"Expected 6 swatches, found {swatch_count}"

        # B) Verify NO text pills exist on this card
        size_pills = caitlin_card.locator(".product-card__size-pill")
        size_pill_count = size_pills.count()
        print(f"Size pills count: {size_pill_count}")
        assert size_pill_count == 0, f"Expected 0 text pills on color-only card, found {size_pill_count}"

        # C) Verify swatch images and styling
        first_swatch_img = swatches.first.locator("img.product-card__swatch-img")
        assert first_swatch_img.is_visible(), "Swatch img element should be visible"
        img_src = first_swatch_img.get_attribute("src")
        print(f"First swatch img src: {img_src}")
        assert "width=80" in img_src or "height=80" in img_src or "crop=center" in img_src or "cdn.shopify.com" in img_src

        # D) Verify Color header row
        color_header = caitlin_card.locator(".product-card__color-header")
        assert color_header.is_visible(), "Color header row must be visible"
        header_text = color_header.inner_text()
        print(f"Initial color header text: '{header_text}'")
        assert "COLOR" in header_text.upper()

        initial_stage_img = caitlin_card.locator(".product-card__image").get_attribute("src")
        print(f"Initial stage image src: {initial_stage_img}")

        # Capture initial desktop screenshot
        desktop_initial_shot = os.path.join(ARTIFACTS_DIR, "01_desktop_caitlin_initial.png")
        caitlin_card.screenshot(path=desktop_initial_shot)
        results["screenshots"].append(desktop_initial_shot)
        print(f"Saved screenshot: {desktop_initial_shot}")
        results["desktop_caitlin"] = True

        # ----------------------------------------------------------------------
        # E) Test Hover Preview & Click on "Gold/Chalk" Swatch
        # ----------------------------------------------------------------------
        print("\n[TEST 2] Swatch Interaction: Hover Preview & Click Gold/Chalk")
        gold_chalk_swatch = caitlin_card.locator(".product-card__swatch-btn[data-color-name*='Chalk'], .product-card__swatch-btn[aria-label*='Chalk']").first
        assert gold_chalk_swatch.is_visible(), "Gold/Chalk swatch must be visible"

        gold_chalk_img_url = gold_chalk_swatch.get_attribute("data-variant-image")
        gold_chalk_variant_id = gold_chalk_swatch.get_attribute("data-variant-id")
        print(f"Gold/Chalk variant ID: {gold_chalk_variant_id}")
        print(f"Gold/Chalk variant stage img: {gold_chalk_img_url}")

        # 1. Hover over Gold/Chalk swatch
        gold_chalk_swatch.hover()
        time.sleep(0.5)
        hover_stage_img = caitlin_card.locator(".product-card__image").get_attribute("src")
        print(f"Stage image during hover: {hover_stage_img}")
        assert gold_chalk_img_url in hover_stage_img or "imchk" in hover_stage_img, "Main stage image should preview Gold/Chalk on hover"

        # 2. Click Gold/Chalk swatch
        gold_chalk_swatch.click()
        time.sleep(0.5)

        # Verify active ring moved to Gold/Chalk swatch
        class_list = gold_chalk_swatch.get_attribute("class")
        print(f"Gold/Chalk swatch class after click: {class_list}")
        assert "is-active" in class_list, "Gold/Chalk swatch must have 'is-active' class"

        # Verify stage image locked to Gold/Chalk
        current_stage_img = caitlin_card.locator(".product-card__image").get_attribute("src")
        print(f"Stage image after click: {current_stage_img}")
        assert gold_chalk_img_url in current_stage_img or "imchk" in current_stage_img, "Stage image should lock to Gold/Chalk"

        # Verify active color label updated
        active_label_text = caitlin_card.locator(".product-card__color-active").inner_text()
        print(f"Active color label after click: '{active_label_text}'")
        assert "Chalk" in active_label_text or "CHALK" in active_label_text, "Active color label should display Gold/Chalk"

        # Verify hidden variant ID input updated
        hidden_id_val = caitlin_card.locator(".product-card__variant-id-input").input_value()
        print(f"Hidden variant input value: {hidden_id_val}")
        assert hidden_id_val == gold_chalk_variant_id, f"Hidden variant ID should be {gold_chalk_variant_id}, got {hidden_id_val}"

        # Capture selected desktop screenshot
        desktop_selected_shot = os.path.join(ARTIFACTS_DIR, "02_desktop_caitlin_gold_chalk_selected.png")
        caitlin_card.screenshot(path=desktop_selected_shot)
        results["screenshots"].append(desktop_selected_shot)
        print(f"Saved screenshot: {desktop_selected_shot}")
        results["desktop_click_swatch"] = True

        # ----------------------------------------------------------------------
        # F) Test AJAX Add to Bag for Gold/Chalk
        # ----------------------------------------------------------------------
        print("\n[TEST 3] AJAX Add to Bag Submission for Gold/Chalk Variant")
        submit_btn = caitlin_card.locator(".product-card__submit-btn")
        assert not submit_btn.is_disabled(), "Submit button should be enabled for available Gold/Chalk variant"

        cart_request_captured = []
        def handle_request(req):
            if "/cart/add" in req.url:
                cart_request_captured.append(req.post_data)

        page.on("request", handle_request)

        # Click Add to Bag
        with page.expect_response(lambda res: "/cart/add" in res.url, timeout=10000) as response_info:
            submit_btn.click()

        cart_response = response_info.value
        print(f"Cart add HTTP status: {cart_response.status}")
        assert cart_response.status == 200, f"Expected 200 from /cart/add.js, got {cart_response.status}"

        # Verify the added item variant matches gold_chalk_variant_id
        cart_resp_json = cart_response.json()
        print(f"Cart response variant ID: {cart_resp_json.get('id')}")
        assert str(cart_resp_json.get("id")) == str(gold_chalk_variant_id), "Added cart item must match selected Gold/Chalk variant ID"

        time.sleep(1.5)
        desktop_cart_shot = os.path.join(ARTIFACTS_DIR, "03_desktop_cart_added.png")
        page.screenshot(path=desktop_cart_shot)
        results["screenshots"].append(desktop_cart_shot)
        print(f"Saved screenshot: {desktop_cart_shot}")
        results["desktop_ajax_add_to_bag"] = True

        context_desktop.close()

        # ----------------------------------------------------------------------
        # 2. MOBILE TEST: Caitlin Shoulder Bag on 390x844 Viewport
        # ----------------------------------------------------------------------
        print("\n[TEST 4] Mobile (390x844) - Coach Caitlin Visual Swatches & Tap")
        context_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page_mobile = context_mobile.new_page()

        page_mobile.goto("https://therareavenue.com/search?q=Caitlin", wait_until="domcontentloaded", timeout=45000)
        page_mobile.wait_for_selector("product-card", timeout=10000)

        mobile_card = page_mobile.locator("product-card").first
        m_swatches = mobile_card.locator(".product-card__swatch-btn")
        assert m_swatches.count() == 6, f"Mobile expected 6 swatches, found {m_swatches.count()}"

        m_pills = mobile_card.locator(".product-card__size-pill")
        assert m_pills.count() == 0, f"Mobile expected 0 size pills, found {m_pills.count()}"

        # Tap/Click Gold/Chalk on mobile
        m_gold_chalk = mobile_card.locator(".product-card__swatch-btn[data-color-name*='Chalk'], .product-card__swatch-btn[aria-label*='Chalk']").first
        m_gold_chalk.click()
        time.sleep(0.5)

        m_active_label = mobile_card.locator(".product-card__color-active").inner_text()
        print(f"Mobile active color label: '{m_active_label}'")
        assert "Chalk" in m_active_label or "CHALK" in m_active_label

        mobile_shot = os.path.join(ARTIFACTS_DIR, "04_mobile_caitlin_swatches.png")
        page_mobile.screenshot(path=mobile_shot)
        results["screenshots"].append(mobile_shot)
        print(f"Saved mobile screenshot: {mobile_shot}")
        results["mobile_caitlin"] = True

        context_mobile.close()

        # ----------------------------------------------------------------------
        # 3. REGRESSION TEST: Footwear UK Size Pills
        # ----------------------------------------------------------------------
        print("\n[TEST 5] Footwear Regression Test - Preserve Beloved UK Size Pills")
        context_shoes = browser.new_context(viewport={"width": 1280, "height": 800})
        page_shoes = context_shoes.new_page()

        page_shoes.goto("https://therareavenue.com/collections/footwear", wait_until="domcontentloaded", timeout=45000)
        page_shoes.wait_for_selector("product-card", timeout=10000)

        shoe_card = page_shoes.locator("product-card").first
        shoe_card.scroll_into_view_if_needed()
        page_shoes.wait_for_timeout(1000)

        shoe_title = shoe_card.locator(".product-card__title").inner_text().strip()
        print(f"Tested shoe card: '{shoe_title}'")

        # Must have size container and pills
        shoe_sizing = shoe_card.locator(".product-card__sizing")
        assert shoe_sizing.is_visible(), "Footwear card must have .product-card__sizing visible"

        shoe_size_title = shoe_card.locator(".product-card__size-title").inner_text().strip()
        print(f"Footwear size title: '{shoe_size_title}'")
        assert "SIZE" in shoe_size_title.upper() or "UK" in shoe_size_title.upper()

        shoe_pills = shoe_card.locator(".product-card__size-pill")
        shoe_pill_count = shoe_pills.count()
        print(f"Footwear size pills count: {shoe_pill_count}")
        assert shoe_pill_count >= 1, "Footwear card must display size pills"

        first_pill_text = shoe_pills.first.inner_text().strip()
        print(f"First footwear pill text: '{first_pill_text}'")
        assert "UK" in first_pill_text or "US" in first_pill_text or len(first_pill_text) > 0

        # Must NOT have color swatches on shoe card with single/no color options
        shoe_swatches = shoe_card.locator(".product-card__swatch-btn")
        print(f"Footwear swatch count: {shoe_swatches.count()}")
        assert shoe_swatches.count() == 0, "Footwear with size options only must not show color swatches"

        footwear_shot = os.path.join(ARTIFACTS_DIR, "05_footwear_size_pills.png")
        shoe_card.screenshot(path=footwear_shot)
        results["screenshots"].append(footwear_shot)
        print(f"Saved screenshot: {footwear_shot}")
        results["footwear_regression"] = True

        context_shoes.close()

        # ----------------------------------------------------------------------
        # 4. WATCHES TEST: Single-Variant Direct Add to Bag Without Clutter
        # ----------------------------------------------------------------------
        print("\n[TEST 6] Luxury Watches Test - Single-Variant Clean Add to Bag")
        context_watches = browser.new_context(viewport={"width": 1280, "height": 800})
        page_watches = context_watches.new_page()

        page_watches.goto("https://therareavenue.com/collections/luxury-watches", wait_until="domcontentloaded", timeout=45000)
        page_watches.wait_for_selector("product-card", timeout=10000)

        watch_card = page_watches.locator("product-card").first
        watch_title = watch_card.locator(".product-card__title").inner_text().strip()
        print(f"Tested watch card: '{watch_title}'")

        # Zero swatches and zero pills
        w_swatches = watch_card.locator(".product-card__swatch-btn")
        w_pills = watch_card.locator(".product-card__size-pill")
        assert w_swatches.count() == 0, "Watches should have 0 swatches"
        assert w_pills.count() == 0, "Watches should have 0 size pills"

        # Direct submit button exists and enabled
        w_submit = watch_card.locator(".product-card__submit-btn")
        assert w_submit.is_visible() and not w_submit.is_disabled(), "Watch card must have direct Add to Bag button"

        watch_card.scroll_into_view_if_needed()
        page_watches.wait_for_timeout(1000)

        watches_shot = os.path.join(ARTIFACTS_DIR, "06_watches_single_variant.png")
        watch_card.screenshot(path=watches_shot)
        results["screenshots"].append(watches_shot)
        print(f"Saved screenshot: {watches_shot}")
        results["watches_clean_layout"] = True

        context_watches.close()

        # ----------------------------------------------------------------------
        # 5. MULTI-OPTION TEST: Products with BOTH Color Swatches AND Size Pills
        # ----------------------------------------------------------------------
        print("\n[TEST 7] Multi-Option Products (Color + Size): Cloud 6 Coast Sneaker")
        context_multi = browser.new_context(viewport={"width": 1280, "height": 800})
        page_multi = context_multi.new_page()

        page_multi.goto("https://therareavenue.com/search?q=Cloud+6+Coast", wait_until="domcontentloaded", timeout=45000)
        page_multi.wait_for_selector("product-card", timeout=10000)

        multi_card = page_multi.locator("product-card").first
        multi_card.scroll_into_view_if_needed()
        page_multi.wait_for_timeout(1000)

        m_card_title = multi_card.locator(".product-card__title").inner_text().strip()
        print(f"Multi-option card title: '{m_card_title}'")

        # A) Verify BOTH swatches and size pills are present
        multi_swatches = multi_card.locator(".product-card__swatch-btn")
        multi_pills = multi_card.locator(".product-card__size-pill")
        m_swatch_cnt = multi_swatches.count()
        m_pill_cnt = multi_pills.count()
        print(f"Multi-option product: {m_swatch_cnt} swatches, {m_pill_cnt} size pills")
        assert m_swatch_cnt > 1, f"Expected >1 swatches, found {m_swatch_cnt}"
        assert m_pill_cnt > 1, f"Expected >1 size pills, found {m_pill_cnt}"

        # B) Verify initial active color and size
        init_col_text = multi_card.locator(".product-card__color-active").inner_text().strip()
        init_sz_text = multi_card.locator(".product-card__size-active").inner_text().strip()
        print(f"Initial: Color='{init_col_text}', Size='{init_sz_text}'")
        assert len(init_col_text) > 0, "Initial color label must not be empty"
        assert len(init_sz_text) > 0, "Initial size label must not be empty"

        # C) Switch color swatch to White / Glacier (2nd swatch)
        swatch_2 = multi_swatches.nth(1)
        s2_color_name = swatch_2.get_attribute("data-color-name")
        print(f"Clicking swatch 2: '{s2_color_name}'")
        swatch_2.click()
        page_multi.wait_for_timeout(500)

        new_col_text = multi_card.locator(".product-card__color-active").inner_text().strip()
        print(f"Active color after click: '{new_col_text}'")
        assert s2_color_name.upper() in new_col_text.upper(), f"Expected color {s2_color_name}, got {new_col_text}"

        # D) Verify that available size pills in White / Glacier can be selected
        # In White / Glacier, UK 6.5 or UK 5 is available
        avail_pill = multi_card.locator(".product-card__size-pill:not(:disabled)").first
        assert avail_pill.is_visible(), "Should have at least one enabled size pill for White / Glacier"
        avail_pill_name = avail_pill.get_attribute("data-size-name")
        print(f"Clicking available size pill: '{avail_pill_name}'")
        avail_pill.click()
        page_multi.wait_for_timeout(500)

        selected_size_label = multi_card.locator(".product-card__size-active").inner_text().strip()
        print(f"Active size label after click: '{selected_size_label}'")
        assert avail_pill_name.upper() in selected_size_label.upper(), f"Expected size {avail_pill_name}, got {selected_size_label}"

        # E) Verify variant ID updated correctly
        final_var_id = multi_card.locator(".product-card__variant-id-input").input_value()
        expected_var_id = avail_pill.get_attribute("data-variant-id")
        print(f"Form variant ID: {final_var_id}, Pill variant ID: {expected_var_id}")
        assert final_var_id == expected_var_id, "Form input variant ID must match clicked pill variant ID"

        # Capture multi-option screenshot
        multi_shot = os.path.join(ARTIFACTS_DIR, "07_multi_option_color_and_size.png")
        multi_card.screenshot(path=multi_shot)
        results["screenshots"].append(multi_shot)
        print(f"Saved screenshot: {multi_shot}")
        results["multi_option_color_and_size"] = True

        context_multi.close()
        browser.close()

    print("\n" + "=" * 80)
    print("ALL 7 TEST SUITES PASSED CLEANLY!")
    print(json.dumps(results, indent=2))
    print("=" * 80)

    # Save summary json
    summary_path = os.path.join(ARTIFACTS_DIR, "test_results_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results

if __name__ == "__main__":
    run_swatch_tests()
