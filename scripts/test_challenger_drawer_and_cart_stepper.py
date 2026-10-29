#!/usr/bin/env python3
"""
Empirical Stress Test: Slide-Out Drawer & Cart Page Quantity Stepping & Boundary Validation
Target Storefront: https://therareavenue.com

Explicit Mission Verification:
1. 1->2 increment (drawer + page)
2. 2->1 decrement (drawer + page)
3. Zeroing (via decrement/direct input 0/remove)
4. Single certificate detachment (preserves parent product, re-enables + Add prompt)
5. Cart bubble count consistency across drawer, cart page, and header
"""

import sys
import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.async_api import async_playwright, Page, Browser

STOREFRONT_URL = "https://therareavenue.com"
CHECKCHECK_VARIANT_ID = 57721101779110

COACH_HANDLE = "pouch-in-signature-canvas"
COACH_VARIANT = 57530143768742

MK_HANDLE = "cherie-leather-sandal"
MK_VARIANT = 57546840965286

class DrawerAndCartStepperChallenger:
    def __init__(self, headless: bool = True, channel: str = "msedge"):
        self.headless = headless
        self.channel = channel
        self.results: List[Dict[str, Any]] = []

    def record(self, step_id: str, title: str, passed: bool, details: Dict[str, Any]):
        status = "PASS" if passed else "FAIL"
        mark = "✓" if passed else "✗"
        res = {
            "step_id": step_id,
            "title": title,
            "status": status,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.results.append(res)
        print(f"[{mark}] [{step_id}] {title} -> {status}")
        if not passed:
            print(f"    FAILURE DETAILS: {json.dumps(details, indent=2)}")

    async def clear_cart(self, page: Page):
        try:
            await page.evaluate("""
                fetch('/cart/clear.js', {
                    method: 'POST',
                    headers: {'Accept': 'application/json'}
                }).then(r => r.json()).catch(() => ({}))
            """)
            await page.wait_for_timeout(1000)
        except Exception:
            pass

    async def get_cart(self, page: Page) -> Dict[str, Any]:
        try:
            return await page.evaluate("fetch('/cart.js').then(r => r.json())")
        except Exception:
            return {}

    async def get_cart_bubble(self, page: Page) -> int:
        bubble = page.locator("[ref='cartBubbleCount'], [data-testid='cart-bubble'], .cart-bubble__text-count, .cart-count-bubble").first
        if await bubble.count() > 0 and await bubble.is_visible():
            txt = (await bubble.inner_text()).strip()
            if txt.isdigit():
                return int(txt)
        return 0

    async def run(self) -> int:
        print("\n" + "="*80)
        print("EMPIRICAL CHALLENGER: DRAWER & CART PAGE STEPPER STRESS HARNESS")
        print("="*80)

        p = await async_playwright().start()
        try:
            try:
                browser = await p.chromium.launch(channel=self.channel, headless=self.headless)
            except Exception:
                browser = await p.chromium.launch(headless=self.headless)

            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                # -------------------------------------------------------------
                # PHASE 1: SLIDE-OUT DRAWER QUANTITY STEPPING & DETACHMENT
                # -------------------------------------------------------------
                print("\n--- PHASE 1: Slide-Out Drawer Interactivity ---")
                await self.clear_cart(page)

                # Add Coach bag with CheckCheck from PDP
                await page.goto(f"{STOREFRONT_URL}/products/{COACH_HANDLE}", timeout=30000)
                await page.wait_for_timeout(1500)

                cc_box = page.locator("#checkcheck-addon-checkbox").first
                await cc_box.scroll_into_view_if_needed()
                if not await cc_box.is_checked():
                    await cc_box.check()
                await page.wait_for_timeout(500)

                atc_btn = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
                await atc_btn.click()
                await page.wait_for_timeout(4000)

                # Open drawer if not already open
                drawer = page.locator("cart-drawer-component, #cart-drawer, theme-drawer#cart-drawer").first
                drawer_open = await drawer.count() > 0
                if not drawer_open or not await drawer.is_visible():
                    cart_trigger = page.locator("header a[href='/cart'], [ref='cartIcon']").first
                    if await cart_trigger.count() > 0:
                        await cart_trigger.click()
                        await page.wait_for_timeout(2000)

                cart_1 = await self.get_cart(page)
                items_1 = cart_1.get("items", [])
                p_qty_1 = next((it.get("quantity", 0) for it in items_1 if it.get("variant_id") == COACH_VARIANT), 0)
                c_qty_1 = next((it.get("quantity", 0) for it in items_1 if it.get("variant_id") == CHECKCHECK_VARIANT_ID), 0)
                bubble_1 = await self.get_cart_bubble(page)

                p1_pass = (p_qty_1 == 1 and c_qty_1 == 1 and bubble_1 == 1)
                self.record("DRAWER-1", "PDP ATC bundles item + cert: Coach=1, Cert=1, Bubble=1",
                            p1_pass, {"coach": p_qty_1, "cert": c_qty_1, "bubble": bubble_1})

                # Step 1.2: Drawer 1 -> 2 Increment
                print("\n[Action] Incrementing Coach quantity 1 -> 2 in drawer...")
                drawer_plus_btn = page.locator("theme-drawer#cart-drawer button[name='plus'], cart-drawer-component button[name='plus'], .cart-drawer button[name='plus'], [data-line-variant] button[name='plus']").first
                if await drawer_plus_btn.count() > 0:
                    await drawer_plus_btn.click()
                    await page.wait_for_timeout(4500)

                cart_2 = await self.get_cart(page)
                items_2 = cart_2.get("items", [])
                p_qty_2 = next((it.get("quantity", 0) for it in items_2 if it.get("variant_id") == COACH_VARIANT), 0)
                c_qty_2 = next((it.get("quantity", 0) for it in items_2 if it.get("variant_id") == CHECKCHECK_VARIANT_ID), 0)
                bubble_2 = await self.get_cart_bubble(page)

                p2_pass = (p_qty_2 == 2 and c_qty_2 == 2 and bubble_2 == 2)
                self.record("DRAWER-2", "Drawer 1 -> 2 Increment: Lockstep Coach=2, Cert=2, Bubble=2 (NOT 4)",
                            p2_pass, {"coach": p_qty_2, "cert": c_qty_2, "bubble": bubble_2})

                # Step 1.3: Drawer 2 -> 1 Decrement
                print("\n[Action] Decrementing Coach quantity 2 -> 1 in drawer...")
                drawer_minus_btn = page.locator("theme-drawer#cart-drawer button[name='minus'], cart-drawer-component button[name='minus'], .cart-drawer button[name='minus'], [data-line-variant] button[name='minus']").first
                if await drawer_minus_btn.count() > 0:
                    await drawer_minus_btn.click()
                    await page.wait_for_timeout(4500)

                cart_3 = await self.get_cart(page)
                items_3 = cart_3.get("items", [])
                p_qty_3 = next((it.get("quantity", 0) for it in items_3 if it.get("variant_id") == COACH_VARIANT), 0)
                c_qty_3 = next((it.get("quantity", 0) for it in items_3 if it.get("variant_id") == CHECKCHECK_VARIANT_ID), 0)
                bubble_3 = await self.get_cart_bubble(page)

                p3_pass = (p_qty_3 == 1 and c_qty_3 == 1 and bubble_3 == 1)
                self.record("DRAWER-3", "Drawer 2 -> 1 Decrement: Lockstep Coach=1, Cert=1, Bubble=1 (NOT 2)",
                            p3_pass, {"coach": p_qty_3, "cert": c_qty_3, "bubble": bubble_3})

                # Step 1.4: Detach certificate only via [Remove]
                print("\n[Action] Detaching certificate only in drawer...")
                remove_cert_btn = page.locator(".ra-remove-cert-btn").first
                if await remove_cert_btn.count() > 0:
                    await remove_cert_btn.click()
                    await page.wait_for_timeout(4000)

                cart_4 = await self.get_cart(page)
                items_4 = cart_4.get("items", [])
                p_qty_4 = next((it.get("quantity", 0) for it in items_4 if it.get("variant_id") == COACH_VARIANT), 0)
                c_qty_4 = next((it.get("quantity", 0) for it in items_4 if it.get("variant_id") == CHECKCHECK_VARIANT_ID), 0)
                bubble_4 = await self.get_cart_bubble(page)
                add_cert_btn_present = await page.locator(".ra-add-cert-btn").count() > 0

                p4_pass = (p_qty_4 == 1 and c_qty_4 == 0 and (bubble_4 is None or bubble_4 == 1) and add_cert_btn_present)
                self.record("DRAWER-4", "Detach certificate: Coach=1 remains intact, Cert=0, + Add prompt appears, Bubble=1",
                            p4_pass, {"coach": p_qty_4, "cert": c_qty_4, "bubble": bubble_4, "add_btn_present": add_cert_btn_present})

                # Step 1.5: Re-attach certificate via "+ Add CheckCheck Certificate" button
                print("\n[Action] Re-attaching certificate via + Add CheckCheck Certificate...")
                add_cert_btn = page.locator(".ra-add-cert-btn").first
                if await add_cert_btn.count() > 0:
                    await add_cert_btn.click()
                    await page.wait_for_timeout(4000)

                cart_5 = await self.get_cart(page)
                items_5 = cart_5.get("items", [])
                p_qty_5 = next((it.get("quantity", 0) for it in items_5 if it.get("variant_id") == COACH_VARIANT), 0)
                c_qty_5 = next((it.get("quantity", 0) for it in items_5 if it.get("variant_id") == CHECKCHECK_VARIANT_ID), 0)
                bubble_5 = await self.get_cart_bubble(page)

                p5_pass = (p_qty_5 == 1 and c_qty_5 == 1 and (bubble_5 is None or bubble_5 == 1))
                self.record("DRAWER-5", "Re-attach certificate in drawer: Coach=1, Cert=1, Bubble=1",
                            p5_pass, {"coach": p_qty_5, "cert": c_qty_5, "bubble": bubble_5})

                # Step 1.6: Remove parent product with attached cert -> Atomic zeroing
                print("\n[Action] Removing parent product with attached cert...")
                remove_product_btn = page.locator("button.cart-items__remove").first
                if await remove_product_btn.count() > 0:
                    await remove_product_btn.click()
                    await page.wait_for_timeout(4000)

                cart_6 = await self.get_cart(page)
                items_6 = cart_6.get("items", [])
                bubble_6 = await self.get_cart_bubble(page)

                p6_pass = (len(items_6) == 0 and (bubble_6 is None or bubble_6 == 0))
                self.record("DRAWER-6", "Atomic removal of parent removes certificate: 0 items, 0 orphans, Bubble=0",
                            p6_pass, {"items_count": len(items_6), "bubble": bubble_6})

                # -------------------------------------------------------------
                # PHASE 2: CART PAGE (/cart) DIRECT INPUT & PARITY
                # -------------------------------------------------------------
                print("\n--- PHASE 2: Cart Page (/cart) Direct Input & Parity ---")
                await self.clear_cart(page)

                # Add MK sandals with CheckCheck
                await page.goto(f"{STOREFRONT_URL}/products/{MK_HANDLE}", timeout=30000)
                await page.wait_for_timeout(1500)

                cc_box_mk = page.locator("#checkcheck-addon-checkbox").first
                await cc_box_mk.scroll_into_view_if_needed()
                if not await cc_box_mk.is_checked():
                    await cc_box_mk.check()
                await page.wait_for_timeout(500)

                atc_mk = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
                await atc_mk.click()
                await page.wait_for_timeout(3500)

                # Navigate directly to /cart page
                await page.goto(f"{STOREFRONT_URL}/cart", timeout=30000)
                await page.wait_for_timeout(2000)

                cart_page_initial = await self.get_cart(page)
                items_page = cart_page_initial.get("items", [])
                mk_qty_1 = next((it.get("quantity", 0) for it in items_page if it.get("variant_id") == MK_VARIANT), 0)
                c_mk_1 = next((it.get("quantity", 0) for it in items_page if it.get("variant_id") == CHECKCHECK_VARIANT_ID), 0)
                bubble_page_1 = await self.get_cart_bubble(page)
                cert_box_rendered = await page.locator(".ra-attached-cert-box").count() > 0

                p7_pass = (mk_qty_1 == 1 and c_mk_1 == 1 and cert_box_rendered and (bubble_page_1 is None or bubble_page_1 == 1))
                self.record("PAGE-1", "/cart page renders attached cert box: MK=1, Cert=1, Bubble=1",
                            p7_pass, {"mk_qty": mk_qty_1, "cert_qty": c_mk_1, "cert_box_rendered": cert_box_rendered, "bubble": bubble_page_1})

                # Direct input: Fill '2' via keyboard
                print("\n[Action] Entering '2' into quantity input on /cart...")
                qty_input = page.locator("input.quantity__input, input[name='updates[]'], .quantity-selector input[type='number']").first
                if await qty_input.count() > 0:
                    await qty_input.fill("2")
                    await qty_input.dispatch_event("change")
                    await qty_input.press("Enter")
                    await page.wait_for_timeout(4000)

                cart_page_2 = await self.get_cart(page)
                items_page_2 = cart_page_2.get("items", [])
                mk_qty_2 = next((it.get("quantity", 0) for it in items_page_2 if it.get("variant_id") == MK_VARIANT), 0)
                c_mk_2 = next((it.get("quantity", 0) for it in items_page_2 if it.get("variant_id") == CHECKCHECK_VARIANT_ID), 0)
                bubble_page_2 = await self.get_cart_bubble(page)

                p8_pass = (mk_qty_2 == 2 and c_mk_2 == 2 and (bubble_page_2 is None or bubble_page_2 == 2))
                self.record("PAGE-2", "Direct keyboard input '2' scales attached cert to 2 in lockstep: MK=2, Cert=2, Bubble=2",
                            p8_pass, {"mk_qty": mk_qty_2, "cert_qty": c_mk_2, "bubble": bubble_page_2})

                # Direct input zeroing: Fill '0' via keyboard
                print("\n[Action] Entering '0' into quantity input on /cart to test keyboard zeroing...")
                if await qty_input.count() > 0:
                    await qty_input.fill("0")
                    await qty_input.dispatch_event("change")
                    await qty_input.press("Enter")
                    await page.wait_for_timeout(4000)

                cart_page_0 = await self.get_cart(page)
                items_page_0 = cart_page_0.get("items", [])
                bubble_page_0 = await self.get_cart_bubble(page)

                p9_pass = (len(items_page_0) == 0 and (bubble_page_0 is None or bubble_page_0 == 0))
                self.record("PAGE-3", "Direct keyboard input '0' cleanly eliminates product and certificate: 0 items, Bubble=0",
                            p9_pass, {"items_count": len(items_page_0), "bubble": bubble_page_0})

            finally:
                await self.clear_cart(page)
                await page.close()
                await context.close()
                await browser.close()
        finally:
            await p.stop()

        failed_count = len([r for r in self.results if r["status"] == "FAIL"])
        print("\n" + "="*80)
        print(f"DRAWER & CART STRESS HARNESS COMPLETE: {len(self.results) - failed_count}/{len(self.results)} PASSED")
        print("="*80)
        return 0 if failed_count == 0 else 1

async def main():
    challenger = DrawerAndCartStepperChallenger(headless=True)
    exit_code = await challenger.run()

    # Save structured results
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", ".agents", "teamwork", "challenger_it2_2", "drawer_cart_stepper_report.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(challenger.results, f, indent=2, ensure_ascii=False)
    print(f"Saved results to: {out_path}")
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
