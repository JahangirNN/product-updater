"""
Empirical Challenger M1.2 Verification & Adversarial Stress Test Suite
Author: Challenger M1.2 (critic, specialist)
Tests browser facet interactions, mobile drawer auto-closing, desktop sidebar faceting,
and active chip dismissal using Playwright across mobile and desktop viewports.
"""

import os
import sys
import re
import time
from playwright.sync_api import sync_playwright

LOCAL_THEME_JS = os.path.abspath("theme/assets/theme.js")

def run_tests():
    print("=" * 80)
    print("CHALLENGER M1.2: EMPIRICAL PLAYWRIGHT FACET & MOBILE DRAWER TEST SUITE")
    print("=" * 80)

    with open(LOCAL_THEME_JS, "r", encoding="utf-8") as f:
        local_theme_js = f.read()

    def route_theme_js(route):
        route.fulfill(
            status=200,
            content_type="application/javascript; charset=utf-8",
            body=local_theme_js
        )

    all_tests_passed = True
    test_results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ---------------------------------------------------------------------
        # 1. MOBILE VIEWPORT (430x932 - iPhone 14 Pro Max)
        # ---------------------------------------------------------------------
        print("\n[TEST 1] Mobile Viewport (430x932) - Facets Drawer & Facet Click")
        ctx_mobile = browser.new_context(
            viewport={"width": 430, "height": 932},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page_m = ctx_mobile.new_page()
        page_m.route("**/assets/theme.js*", route_theme_js)
        page_m.route("**/theme.js*", route_theme_js)

        errors_m = []
        page_m.on("pageerror", lambda e: errors_m.append(str(e)))

        page_m.goto("https://therareavenue.com/collections/luxury-watches", wait_until="domcontentloaded", timeout=45000)
        page_m.wait_for_timeout(2000)

        page_m.evaluate("""
            window.__events = {
                facetUpdate: [],
                loadingStart: 0,
                loadingEnd: 0
            };
            document.addEventListener('facet:update', (e) => {
                window.__events.facetUpdate.push({
                    url: e.detail?.url?.toString(),
                    sectionId: e.detail?.url?.searchParams?.get('section_id')
                });
            });
            document.documentElement.addEventListener('theme:loading:start', () => {
                window.__events.loadingStart++;
            });
            document.documentElement.addEventListener('theme:loading:end', () => {
                window.__events.loadingEnd++;
            });
        """)

        # Open Filter Drawer
        btn_filter = page_m.query_selector("button[aria-controls='facets-drawer']")
        assert btn_filter, "Filter button not found on mobile page!"
        btn_filter.click()
        page_m.wait_for_timeout(800)

        # Verify drawer is reparented to body and opened
        drawer_before = page_m.evaluate("""
            () => {
                const d = document.querySelector('facets-drawer');
                return {
                    isBody: d.parentElement === document.body,
                    isOpen: d.hasAttribute('open')
                };
            }
        """)
        print("  Mobile drawer opened & reparented to body:", drawer_before)
        assert drawer_before['isBody'] == True, "Mobile drawer was not reparented to document.body!"
        assert drawer_before['isOpen'] == True, "Mobile drawer is not open!"

        # Open GENDER accordion
        summary_gender = page_m.query_selector("facets-drawer details:has(summary:has-text('GENDER')) summary")
        assert summary_gender, "GENDER summary not found in mobile drawer!"
        summary_gender.click()
        page_m.wait_for_timeout(500)

        # Click Men link inside drawer
        link_men = page_m.query_selector("facets-drawer a[href*='/men']")
        assert link_men, "Men's facet link not found in mobile drawer!"
        print("  Tapping Men's facet link inside detached drawer...")
        link_men.click()
        page_m.wait_for_timeout(3000)

        drawer_after = page_m.evaluate("""
            () => {
                const d = document.querySelector('facets-drawer');
                return {
                    isOpen: d.hasAttribute('open')
                };
            }
        """)
        print("  Mobile drawer open state after tap:", drawer_after['isOpen'])
        events_m = page_m.evaluate("() => window.__events")
        print("  facet:update events emitted:", events_m['facetUpdate'])
        print("  Loading events count (start/end):", events_m['loadingStart'], events_m['loadingEnd'])
        print("  JavaScript runtime errors:", errors_m)

        pass_t1 = (
            len(errors_m) == 0 and
            drawer_after['isOpen'] == False and
            len(events_m['facetUpdate']) >= 1 and
            events_m['facetUpdate'][0]['sectionId'] is not None and
            len(events_m['facetUpdate'][0]['sectionId']) > 0 and
            "template--" in events_m['facetUpdate'][0]['sectionId']
        )
        test_results["Test 1: Mobile (430x932) Drawer & Facet Click"] = "PASS" if pass_t1 else f"FAIL (errors: {errors_m})"
        if not pass_t1: all_tests_passed = False
        print(f"  Result: {'PASS' if pass_t1 else 'FAIL'}")

        # Screenshot
        os.makedirs("scratch/screenshots", exist_ok=True)
        page_m.screenshot(path="scratch/screenshots/01_mobile_430x932_men_filtered.png")
        ctx_mobile.close()

        # ---------------------------------------------------------------------
        # 2. MOBILE VIEWPORT (390x844 - iPhone 12/13/14)
        # ---------------------------------------------------------------------
        print("\n[TEST 2] Mobile Viewport (390x844) - Brand Filter Selection")
        ctx_m2 = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page_m2 = ctx_m2.new_page()
        page_m2.route("**/assets/theme.js*", route_theme_js)
        page_m2.route("**/theme.js*", route_theme_js)

        errors_m2 = []
        page_m2.on("pageerror", lambda e: errors_m2.append(str(e)))
        page_m2.goto("https://therareavenue.com/collections/luxury-watches", wait_until="domcontentloaded", timeout=45000)
        page_m2.wait_for_timeout(2000)

        page_m2.evaluate("""
            window.__events = { facetUpdate: [] };
            document.addEventListener('facet:update', (e) => {
                window.__events.facetUpdate.push({
                    url: e.detail?.url?.toString(),
                    sectionId: e.detail?.url?.searchParams?.get('section_id')
                });
            });
        """)

        btn_filter2 = page_m2.query_selector("button[aria-controls='facets-drawer']")
        btn_filter2.click()
        page_m2.wait_for_timeout(800)

        # Open BRAND accordion
        summary_brand = page_m2.query_selector("facets-drawer details:has(summary:has-text('BRAND')) summary")
        assert summary_brand, "BRAND summary not found in mobile drawer!"
        summary_brand.click()
        page_m2.wait_for_timeout(500)

        # Click Tissot link
        link_tissot = page_m2.query_selector("facets-drawer a[href*='/tissot']")
        assert link_tissot, "Tissot facet link not found in mobile drawer!"
        print("  Tapping Tissot facet link inside detached drawer...")
        link_tissot.click()
        page_m2.wait_for_timeout(3000)

        drawer_after_m2 = page_m2.evaluate("() => document.querySelector('facets-drawer').hasAttribute('open')")
        events_m2 = page_m2.evaluate("() => window.__events.facetUpdate")
        print("  Drawer open after click:", drawer_after_m2)
        print("  facet:update events:", events_m2)
        print("  JavaScript runtime errors:", errors_m2)

        pass_t2 = (
            len(errors_m2) == 0 and
            drawer_after_m2 == False and
            len(events_m2) >= 1 and
            events_m2[0]['sectionId'] is not None and
            len(events_m2[0]['sectionId']) > 0
        )
        test_results["Test 2: Mobile (390x844) Brand Facet Tap"] = "PASS" if pass_t2 else f"FAIL (errors: {errors_m2})"
        if not pass_t2: all_tests_passed = False
        print(f"  Result: {'PASS' if pass_t2 else 'FAIL'}")
        page_m2.screenshot(path="scratch/screenshots/02_mobile_390x844_tissot_filtered.png")
        ctx_m2.close()

        # ---------------------------------------------------------------------
        # 3. DESKTOP VIEWPORT (1440x900) - SIDEBAR ACCORDION & FACET LINK
        # ---------------------------------------------------------------------
        print("\n[TEST 3] Desktop Viewport (1440x900) - Sidebar Facet Filtering")
        ctx_desk = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page_d = ctx_desk.new_page()
        page_d.route("**/assets/theme.js*", route_theme_js)
        page_d.route("**/theme.js*", route_theme_js)

        errors_d = []
        page_d.on("pageerror", lambda e: errors_d.append(str(e)))
        page_d.goto("https://therareavenue.com/collections/luxury-watches", wait_until="domcontentloaded", timeout=45000)
        page_d.wait_for_timeout(2000)

        page_d.evaluate("""
            window.__deskEvents = [];
            document.addEventListener('facet:update', (e) => {
                window.__deskEvents.push({
                    url: e.detail?.url?.toString(),
                    sectionId: e.detail?.url?.searchParams?.get('section_id')
                });
            });
        """)

        # On desktop, find GENDER accordion inside .facets-sidebar
        summary_d_gender = page_d.query_selector(".facets-sidebar details:has(summary:has-text('GENDER')) summary")
        assert summary_d_gender, "Desktop GENDER summary in .facets-sidebar not found!"
        print("  Expanding desktop .facets-sidebar GENDER accordion...")
        summary_d_gender.click()
        page_d.wait_for_timeout(500)

        link_d_men = page_d.query_selector(".facets-sidebar a[href*='/men']")
        assert link_d_men, "Desktop Men facet link not found in .facets-sidebar!"
        print("  Clicking desktop Men's facet link...")
        link_d_men.click()
        page_d.wait_for_timeout(3000)

        events_d = page_d.evaluate("() => window.__deskEvents")
        print("  Desktop facet:update events:", events_d)
        print("  Desktop JavaScript errors:", errors_d)

        pass_t3 = (
            len(errors_d) == 0 and
            len(events_d) >= 1 and
            events_d[0]['sectionId'] is not None and
            len(events_d[0]['sectionId']) > 0 and
            "template--" in events_d[0]['sectionId']
        )
        test_results["Test 3: Desktop (1440x900) Sidebar Facet Click"] = "PASS" if pass_t3 else f"FAIL (errors: {errors_d})"
        if not pass_t3: all_tests_passed = False
        print(f"  Result: {'PASS' if pass_t3 else 'FAIL'}")
        page_d.screenshot(path="scratch/screenshots/03_desktop_1440x900_men_filtered.png")
        ctx_desk.close()

        # ---------------------------------------------------------------------
        # 4. ACTIVE FILTER CHIP DISMISSAL AND PARAMETER PRESERVATION
        # ---------------------------------------------------------------------
        print("\n[TEST 4] Active Filter Chip Dismissal & Parameter Preservation")
        ctx_chip = browser.new_context(viewport={"width": 1440, "height": 900})
        page_c = ctx_chip.new_page()
        page_c.route("**/assets/theme.js*", route_theme_js)
        page_c.route("**/theme.js*", route_theme_js)

        errors_c = []
        page_c.on("pageerror", lambda e: errors_c.append(str(e)))

        # Navigate to filtered URL with active query parameter
        url_with_param = "https://therareavenue.com/collections/luxury-watches/men?filter.v.availability=1"
        page_c.goto(url_with_param, wait_until="domcontentloaded", timeout=45000)
        page_c.wait_for_timeout(2000)

        page_c.evaluate("""
            window.__chipEvents = [];
            document.addEventListener('facet:update', (e) => {
                window.__chipEvents.push({
                    url: e.detail?.url?.toString(),
                    sectionId: e.detail?.url?.searchParams?.get('section_id')
                });
            });
        """)

        # Look for removable facet / active chip
        chip_link = page_c.query_selector("a[aria-label*='Remove filter']")
        assert chip_link, "Active filter chip link not found!"
        chip_href = chip_link.get_attribute("href")
        print("  Found active filter chip link href:", chip_href)

        print("  Clicking active filter chip to dismiss...")
        chip_link.click()
        page_c.wait_for_timeout(3000)

        events_c = page_c.evaluate("() => window.__chipEvents")
        print("  Chip dismissal facet:update events:", events_c)
        print("  JavaScript errors during chip dismissal:", errors_c)

        preserved = False
        if events_c:
            target_url = events_c[0]['url']
            print("  Dismissal target URL:", target_url)
            # Verify filter.v.availability=1 was preserved
            if "filter.v.availability=1" in target_url:
                preserved = True
                print("  [SUCCESS] filter.v.availability=1 was correctly preserved in targetUrl!")

        pass_t4 = (len(errors_c) == 0 and len(events_c) >= 1 and preserved)
        test_results["Test 4: Active Chip Dismissal & Parameter Preservation"] = "PASS" if pass_t4 else f"FAIL (errors: {errors_c}, preserved: {preserved})"
        if not pass_t4: all_tests_passed = False
        print(f"  Result: {'PASS' if pass_t4 else 'FAIL'}")
        page_c.screenshot(path="scratch/screenshots/04_desktop_chip_dismissed.png")
        ctx_chip.close()

        # ---------------------------------------------------------------------
        # 5. IN-BROWSER ADVERSARIAL STRESS TEST: EXTRACTSECTIONID & EDGE NODES
        # ---------------------------------------------------------------------
        print("\n[TEST 5] In-Browser Stress Test: extractSectionId Robustness & Edge Nodes")
        page_stress = browser.new_page()
        page_stress.route("**/assets/theme.js*", route_theme_js)
        page_stress.route("**/theme.js*", route_theme_js)
        page_stress.goto("https://therareavenue.com/collections/luxury-watches", wait_until="domcontentloaded", timeout=45000)
        page_stress.wait_for_timeout(1000)

        extract_fn_match = re.search(r'function extractSectionId\(element\) \{[\s\S]*?\n\}', local_theme_js)
        assert extract_fn_match, "extractSectionId function not found in local theme.js"
        fn_code = extract_fn_match.group(0)

        stress_eval = page_stress.evaluate(f"""
            () => {{
                {fn_code}
                const results = [];

                // 1. null element
                try {{
                    const r = extractSectionId(null);
                    results.push({{ test: "null", pass: r === "" }});
                }} catch(e) {{
                    results.push({{ test: "null", pass: false, error: e.message }});
                }}

                // 2. undefined element
                try {{
                    const r = extractSectionId(undefined);
                    results.push({{ test: "undefined", pass: r === "" }});
                }} catch(e) {{
                    results.push({{ test: "undefined", pass: false, error: e.message }});
                }}

                // 3. detached div (simulating unattached drawer or portal)
                try {{
                    const detached = document.createElement("div");
                    const r = extractSectionId(detached);
                    const mainSec = document.querySelector(".shopify-section--main-collection") || document.querySelector(".shopify-section");
                    const expected = mainSec ? mainSec.id.replace("shopify-section-", "") : "";
                    results.push({{ test: "detached_div", pass: r === expected && r.length > 0, value: r }});
                }} catch(e) {{
                    results.push({{ test: "detached_div", pass: false, error: e.message }});
                }}

                // 4. SVG inside button or facet link
                try {{
                    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                    const r = extractSectionId(svg);
                    const mainSec = document.querySelector(".shopify-section--main-collection") || document.querySelector(".shopify-section");
                    const expected = mainSec ? mainSec.id.replace("shopify-section-", "") : "";
                    results.push({{ test: "svg_element", pass: r === expected && r.length > 0, value: r }});
                }} catch(e) {{
                    results.push({{ test: "svg_element", pass: false, error: e.message }});
                }}

                // 5. Text node passed directly
                try {{
                    const textNode = document.createTextNode("Sample Text");
                    const r = extractSectionId(textNode);
                    results.push({{ test: "text_node", pass: typeof r === "string", value: r }});
                }} catch(e) {{
                    results.push({{ test: "text_node", pass: false, error: e.message }});
                }}

                // 6. Element with custom [section-id]
                try {{
                    const container = document.createElement("div");
                    container.setAttribute("section-id", "custom-section-uuid-999");
                    const inner = document.createElement("span");
                    container.appendChild(inner);
                    document.body.appendChild(container);
                    const r = extractSectionId(inner);
                    container.remove();
                    results.push({{ test: "custom_section_id_attr", pass: r === "custom-section-uuid-999", value: r }});
                }} catch(e) {{
                    results.push({{ test: "custom_section_id_attr", pass: false, error: e.message }});
                }}

                // 7. Rapid multi-click facet simulation
                try {{
                    let updateEventsCount = 0;
                    const testHandler = () => updateEventsCount++;
                    document.addEventListener('facet:update', testHandler);

                    const facetLink = document.querySelector('facet-link');
                    if (facetLink) {{
                        for (let i = 0; i < 5; i++) {{
                            facetLink.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }}));
                        }}
                    }}
                    document.removeEventListener('facet:update', testHandler);
                    results.push({{ test: "rapid_clicks", pass: updateEventsCount >= 1, count: updateEventsCount }});
                }} catch(e) {{
                    results.push({{ test: "rapid_clicks", pass: false, error: e.message }});
                }}

                return results;
            }}
        """)

        print("  Stress test matrix results:")
        for st in stress_eval:
            print(f"    [{'PASS' if st.get('pass') else 'FAIL'}] {st.get('test')}: {st}")

        pass_t5 = all(st.get("pass") for st in stress_eval)
        test_results["Test 5: Hostile DOM Stress & Edge Nodes"] = "PASS" if pass_t5 else "FAIL"
        if not pass_t5: all_tests_passed = False
        print(f"  Result: {'PASS' if pass_t5 else 'FAIL'}")
        page_stress.close()

        browser.close()

    # -------------------------------------------------------------------------
    # SUMMARY & FINAL VERDICT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("FINAL SUMMARY OF EMPIRICAL ADVERSARIAL TESTING:")
    for name, status in test_results.items():
        print(f"  - {name}: {status}")
    print("=" * 80)

    verdict = "APPROVE" if all_tests_passed else "REQUEST_CHANGES"
    print(f"\nOVERALL VERDICT: {verdict}")
    return verdict, test_results

if __name__ == "__main__":
    verdict, test_results = run_tests()
    if verdict != "APPROVE":
        sys.exit(1)
