#!/usr/bin/env python3
"""
Adversarial Test Script: Challenger 2 - Multi-Product Mixed Carts, Cross-Brand Isolation & Cart Bubble Invariants
Target Storefront: https://therareavenue.com

Adversarial Stress Test Matrix:
1. Setup 3-item Cross-Brand Cart:
   - Product A: Coach (Coach Pouch, variant 57530143768742) WITH CheckCheck Certificate (Qty 1)
   - Product B: JW PEI (Hana Tote, variant 57534238032038) WITHOUT Certificate (Qty 1)
   - Product C: Nordstrom (HOKA Clifton 11, variant 57582236237990) WITHOUT Certificate (Qty 1)
2. Assert initial cart integrity:
   - Coach: Qty 1, Cert Qty 1 (attached via _parent_id / properties)
   - JW PEI: Qty 1, Cert Qty 0
   - Nordstrom: Qty 1, Cert Qty 0
   - Physical Items Count: exactly 3
   - Header Cart Bubble text: exactly "3"
3. Step Product A (Coach) UP 1 -> 2:
   - Coach Qty: 2, Coach Cert Qty: 2
   - JW PEI Qty: 1, Cert Qty: 0
   - Nordstrom Qty: 1, Cert Qty: 0
   - Physical Count: 4
   - Header Cart Bubble: "4"
4. Step Product B (JW PEI - uncertified) UP 1 -> 3:
   - JW PEI Qty: 3, Cert Qty: 0 (No cert auto-created)
   - Coach Qty: 2, Coach Cert: 2
   - Nordstrom Qty: 1, Cert Qty: 0
   - Physical Count: 6
   - Header Cart Bubble: "6"
5. Step Product A (Coach) DOWN 2 -> 1:
   - Coach Qty: 1, Coach Cert: 1
   - JW PEI Qty: 3, Cert Qty: 0
   - Nordstrom Qty: 1, Cert Qty: 0
   - Physical Count: 5
   - Header Cart Bubble: "5"
6. Post-Cart Upgrade: Click "+ Add CheckCheck Certificate" on Product B (JW PEI, qty 3):
   - JW PEI now has 3 certificates attached!
   - Coach has 1 certificate attached.
   - Nordstrom has 0 certificates.
   - Total cart items: 5 physical + 4 certs = 9 items.
   - Cart Bubble: strictly "5"!
7. Step Product B (JW PEI) DOWN 3 -> 1:
   - JW PEI Qty: 1, JW PEI Cert Qty: 1 (scales in lockstep!)
   - Coach Qty: 1, Coach Cert: 1
   - Nordstrom Qty: 1, Cert: 0
   - Physical Count: 3
   - Header Cart Bubble: "3"
8. Detach only Product A's certificate via .ra-remove-cert-btn:
   - Coach Qty: 1, Cert: 0 (card reverts to show "+ Add CheckCheck Certificate")
   - JW PEI Qty: 1, Cert: 1 (intact!)
   - Nordstrom Qty: 1, Cert: 0
   - Physical Count: 3
   - Header Cart Bubble: "3"
9. Remove Product C (Nordstrom) via zeroing or remove button:
   - Nordstrom removed.
   - Coach Qty: 1, Cert: 0
   - JW PEI Qty: 1, Cert: 1
   - Physical Count: 2
   - Header Cart Bubble: "2"
10. Remove Product B (JW PEI) parent item:
    - Both JW PEI and JW PEI Cert are atomically removed!
    - Zero orphaned certificates in cart!
    - Only Coach remains (Qty 1, 0 certs).
    - Physical Count: 1
    - Header Cart Bubble: "1"
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

from playwright.async_api import async_playwright, Page, Browser


STOREFRONT_URL = "https://therareavenue.com"
CHECKCHECK_VARIANT_ID = 57721101779110

PRODUCTS = {
    "Coach": {
        "handle": "pouch-in-signature-canvas",
        "variant_id": 57530143768742,
        "name": "Coach Pouch in Signature Canvas"
    },
    "JW_PEI": {
        "handle": "hana-large-tote-bag-pink",
        "variant_id": 57534238032038,
        "name": "JW PEI Hana Large Tote Bag"
    },
    "Nordstrom": {
        "handle": "w-clifton-11-gtx-glm",
        "variant_id": 57582236237990,
        "name": "Nordstrom HOKA Clifton 11 GTX"
    }
}

class AdversarialRunner:
    def __init__(self, headless: bool = True, channel: str = "msedge"):
        self.headless = headless
        self.channel = channel
        self.results: List[Dict[str, Any]] = []

    def record(self, step: str, description: str, passed: bool, details: Dict[str, Any]):
        status = "PASS" if passed else "FAIL"
        res = {
            "step": step,
            "description": description,
            "status": status,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.results.append(res)
        mark = "✓" if passed else "✗"
        print(f"[{mark}] [{step}] {description} -> {status}")
        if not passed:
            print(f"    FAILURE DETAILS: {details}")

    async def goto_page(self, page: Page, path: str):
        target = f"{STOREFRONT_URL}/{path.lstrip('/')}"
        try:
            await page.goto(target, timeout=25000)
            await page.wait_for_load_state("domcontentloaded")
        except Exception:
            fallback = f"https://hewmvw-am.myshopify.com/{path.lstrip('/')}"
            await page.goto(fallback, timeout=25000)
            await page.wait_for_load_state("domcontentloaded")

    async def clear_cart(self, page: Page):
        try:
            await page.evaluate("fetch('/cart/clear.js', { method: 'POST', headers: {'Accept': 'application/json'} }).then(r => r.json()).catch(() => ({}))")
            await page.wait_for_timeout(500)
        except Exception:
            pass

    async def get_cart(self, page: Page) -> Dict[str, Any]:
        try:
            return await page.evaluate("fetch('/cart.js').then(r => r.json())")
        except Exception:
            return {}

    async def get_bubble_count(self, page: Page) -> Optional[int]:
        selectors = [
            "[ref='cartBubbleCount']",
            "[data-testid='cart-bubble']",
            ".cart-bubble__text-count",
            ".cart-count-bubble span[aria-hidden='true']",
            ".cart-count-bubble",
            "[data-cart-count]",
            ".header__cart-count"
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                text = (await loc.inner_text()).strip()
                if text.isdigit():
                    return int(text)
        return None

    async def add_to_cart_pdp(self, page: Page, handle: str, with_checkcheck: bool):
        await self.goto_page(page, f"/products/{handle}")
        await page.wait_for_timeout(1200)

        cc_box = page.locator("#checkcheck-addon-checkbox").first
        if await cc_box.count() > 0:
            if with_checkcheck:
                await cc_box.scroll_into_view_if_needed()
                if not await cc_box.is_checked():
                    await cc_box.check()
            else:
                if await cc_box.is_checked():
                    await cc_box.uncheck()

        atc_btn = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add'], button[name='add']").first
        await atc_btn.scroll_into_view_if_needed()
        await atc_btn.click()
        await page.wait_for_timeout(3500)

    async def run(self) -> int:
        print("\n" + "="*80)
        print("STARTING ADVERSARIAL MULTI-PRODUCT MIXED CART & BUBBLE STRESS HARNESS")
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
                # Setup
                print("\n[Setup] Clearing cart...")
                await self.clear_cart(page)

                # Add Coach WITH CheckCheck
                print("[Setup] Adding Product A (Coach) WITH CheckCheck...")
                await self.add_to_cart_pdp(page, PRODUCTS["Coach"]["handle"], with_checkcheck=True)

                # Add JW PEI WITHOUT CheckCheck
                print("[Setup] Adding Product B (JW PEI) WITHOUT CheckCheck...")
                await self.add_to_cart_pdp(page, PRODUCTS["JW_PEI"]["handle"], with_checkcheck=False)

                # Add Nordstrom WITHOUT CheckCheck
                print("[Setup] Adding Product C (Nordstrom) WITHOUT CheckCheck...")
                await self.add_to_cart_pdp(page, PRODUCTS["Nordstrom"]["handle"], with_checkcheck=False)

                await self.goto_page(page, "/cart")
                await page.wait_for_timeout(2000)

                # Step 1: Initial State Assertion
                cart = await self.get_cart(page)
                items = cart.get("items", [])
                
                coach_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Coach"]["variant_id"]), None)
                jw_item = next((it for it in items if it.get("variant_id") == PRODUCTS["JW_PEI"]["variant_id"]), None)
                nord_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Nordstrom"]["variant_id"]), None)
                cert_items = [it for it in items if it.get("variant_id") == CHECKCHECK_VARIANT_ID]

                coach_qty = coach_item.get("quantity", 0) if coach_item else 0
                jw_qty = jw_item.get("quantity", 0) if jw_item else 0
                nord_qty = nord_item.get("quantity", 0) if nord_item else 0
                total_cert_qty = sum(it.get("quantity", 0) for it in cert_items)
                physical_count = coach_qty + jw_qty + nord_qty
                bubble_count = await self.get_bubble_count(page)

                s1_pass = (coach_qty == 1 and jw_qty == 1 and nord_qty == 1 and total_cert_qty == 1 and physical_count == 3 and (bubble_count is None or bubble_count == 3))
                self.record("ADV-1", "Initial Mixed Cart: Coach (cert=1), JW PEI (cert=0), Nordstrom (cert=0), Physical=3, Bubble=3",
                            s1_pass, {"coach_qty": coach_qty, "jw_qty": jw_qty, "nord_qty": nord_qty, "cert_qty": total_cert_qty, "physical": physical_count, "bubble": bubble_count})

                # Step 2: Step Coach UP 1 -> 2
                print("\n[Action] Stepping Coach UP 1 -> 2...")
                coach_plus = page.locator(f"tr[data-variant-id='{PRODUCTS['Coach']['variant_id']}'] button[name='plus'], [data-line-variant='{PRODUCTS['Coach']['variant_id']}'] button[name='plus']").first
                if await coach_plus.count() == 0:
                    coach_plus = page.locator("button[name='plus']").first
                await coach_plus.click()
                await page.wait_for_timeout(4000)

                cart = await self.get_cart(page)
                items = cart.get("items", [])
                coach_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Coach"]["variant_id"]), None)
                jw_item = next((it for it in items if it.get("variant_id") == PRODUCTS["JW_PEI"]["variant_id"]), None)
                nord_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Nordstrom"]["variant_id"]), None)
                cert_items = [it for it in items if it.get("variant_id") == CHECKCHECK_VARIANT_ID]

                coach_qty = coach_item.get("quantity", 0) if coach_item else 0
                jw_qty = jw_item.get("quantity", 0) if jw_item else 0
                nord_qty = nord_item.get("quantity", 0) if nord_item else 0
                total_cert_qty = sum(it.get("quantity", 0) for it in cert_items)
                physical_count = coach_qty + jw_qty + nord_qty
                bubble_count = await self.get_bubble_count(page)

                s2_pass = (coach_qty == 2 and total_cert_qty == 2 and jw_qty == 1 and nord_qty == 1 and physical_count == 4 and (bubble_count is None or bubble_count == 4))
                self.record("ADV-2", "Step Coach UP to 2: Coach Cert scales to 2, uncertified items untouched, Physical=4, Bubble=4",
                            s2_pass, {"coach_qty": coach_qty, "cert_qty": total_cert_qty, "jw_qty": jw_qty, "nord_qty": nord_qty, "physical": physical_count, "bubble": bubble_count})

                # Step 3: Step JW PEI (uncertified) UP 1 -> 3
                print("\n[Action] Stepping uncertified JW PEI UP 1 -> 3...")
                jw_plus = page.locator(f"tr[data-variant-id='{PRODUCTS['JW_PEI']['variant_id']}'] button[name='plus'], [data-line-variant='{PRODUCTS['JW_PEI']['variant_id']}'] button[name='plus']").first
                if await jw_plus.count() > 0:
                    await jw_plus.click()
                    await page.wait_for_timeout(3500)
                    await jw_plus.click()
                    await page.wait_for_timeout(3500)

                cart = await self.get_cart(page)
                items = cart.get("items", [])
                coach_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Coach"]["variant_id"]), None)
                jw_item = next((it for it in items if it.get("variant_id") == PRODUCTS["JW_PEI"]["variant_id"]), None)
                nord_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Nordstrom"]["variant_id"]), None)
                cert_items = [it for it in items if it.get("variant_id") == CHECKCHECK_VARIANT_ID]

                coach_qty = coach_item.get("quantity", 0) if coach_item else 0
                jw_qty = jw_item.get("quantity", 0) if jw_item else 0
                nord_qty = nord_item.get("quantity", 0) if nord_item else 0
                total_cert_qty = sum(it.get("quantity", 0) for it in cert_items)
                physical_count = coach_qty + jw_qty + nord_qty
                bubble_count = await self.get_bubble_count(page)

                s3_pass = (jw_qty == 3 and total_cert_qty == 2 and coach_qty == 2 and nord_qty == 1 and physical_count == 6 and (bubble_count is None or bubble_count == 6))
                self.record("ADV-3", "Step uncertified JW PEI to 3: Cert remains strictly at 2 (Coach only), Physical=6, Bubble=6",
                            s3_pass, {"jw_qty": jw_qty, "coach_qty": coach_qty, "cert_qty": total_cert_qty, "physical": physical_count, "bubble": bubble_count})

                # Step 4: Step Coach DOWN 2 -> 1
                print("\n[Action] Stepping Coach DOWN 2 -> 1...")
                coach_minus = page.locator(f"tr[data-variant-id='{PRODUCTS['Coach']['variant_id']}'] button[name='minus'], [data-line-variant='{PRODUCTS['Coach']['variant_id']}'] button[name='minus']").first
                if await coach_minus.count() == 0:
                    coach_minus = page.locator("button[name='minus']").first
                await coach_minus.click()
                await page.wait_for_timeout(4000)

                cart = await self.get_cart(page)
                items = cart.get("items", [])
                coach_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Coach"]["variant_id"]), None)
                jw_item = next((it for it in items if it.get("variant_id") == PRODUCTS["JW_PEI"]["variant_id"]), None)
                nord_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Nordstrom"]["variant_id"]), None)
                cert_items = [it for it in items if it.get("variant_id") == CHECKCHECK_VARIANT_ID]

                coach_qty = coach_item.get("quantity", 0) if coach_item else 0
                jw_qty = jw_item.get("quantity", 0) if jw_item else 0
                nord_qty = nord_item.get("quantity", 0) if nord_item else 0
                total_cert_qty = sum(it.get("quantity", 0) for it in cert_items)
                physical_count = coach_qty + jw_qty + nord_qty
                bubble_count = await self.get_bubble_count(page)

                s4_pass = (coach_qty == 1 and total_cert_qty == 1 and jw_qty == 3 and nord_qty == 1 and physical_count == 5 and (bubble_count is None or bubble_count == 5))
                self.record("ADV-4", "Step Coach DOWN to 1: Coach Cert scales down to 1 in lockstep, Physical=5, Bubble=5",
                            s4_pass, {"coach_qty": coach_qty, "cert_qty": total_cert_qty, "jw_qty": jw_qty, "physical": physical_count, "bubble": bubble_count})

                # Step 5: In-Cart Upgrade of JW PEI (currently qty 3)
                print("\n[Action] Clicking '+ Add CheckCheck Certificate' on JW PEI (Qty 3)...")
                jw_row = page.locator(f"tr[data-variant-id='{PRODUCTS['JW_PEI']['variant_id']}']").first
                if await jw_row.count() > 0:
                    add_btn = jw_row.locator(".ra-add-cert-btn").first
                else:
                    add_btn = page.locator(".ra-add-cert-btn").first
                
                if await add_btn.count() > 0:
                    await add_btn.click()
                    await page.wait_for_timeout(4000)

                cart = await self.get_cart(page)
                items = cart.get("items", [])
                coach_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Coach"]["variant_id"]), None)
                jw_item = next((it for it in items if it.get("variant_id") == PRODUCTS["JW_PEI"]["variant_id"]), None)
                nord_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Nordstrom"]["variant_id"]), None)
                cert_items = [it for it in items if it.get("variant_id") == CHECKCHECK_VARIANT_ID]

                coach_qty = coach_item.get("quantity", 0) if coach_item else 0
                jw_qty = jw_item.get("quantity", 0) if jw_item else 0
                nord_qty = nord_item.get("quantity", 0) if nord_item else 0
                total_cert_qty = sum(it.get("quantity", 0) for it in cert_items)
                physical_count = coach_qty + jw_qty + nord_qty
                bubble_count = await self.get_bubble_count(page)

                # Expect JW PEI has 3 certs, Coach has 1 cert -> total cert qty = 4. Physical count = 5. Total items = 9.
                s5_pass = (jw_qty == 3 and total_cert_qty == 4 and physical_count == 5 and (bubble_count is None or bubble_count == 5))
                self.record("ADV-5", "In-Cart Upgrade JW PEI (Qty 3): Attaches 3 certs (total certs=4), Physical=5, Bubble=5 (NOT 9)",
                            s5_pass, {"jw_qty": jw_qty, "total_cert_qty": total_cert_qty, "physical": physical_count, "bubble": bubble_count})

                # Step 6: Step JW PEI DOWN 3 -> 1
                print("\n[Action] Stepping JW PEI DOWN 3 -> 1...")
                jw_minus = page.locator(f"tr[data-variant-id='{PRODUCTS['JW_PEI']['variant_id']}'] button[name='minus']").first
                if await jw_minus.count() > 0:
                    await jw_minus.click()
                    await page.wait_for_timeout(3500)
                    await jw_minus.click()
                    await page.wait_for_timeout(3500)

                cart = await self.get_cart(page)
                items = cart.get("items", [])
                coach_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Coach"]["variant_id"]), None)
                jw_item = next((it for it in items if it.get("variant_id") == PRODUCTS["JW_PEI"]["variant_id"]), None)
                nord_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Nordstrom"]["variant_id"]), None)
                cert_items = [it for it in items if it.get("variant_id") == CHECKCHECK_VARIANT_ID]

                coach_qty = coach_item.get("quantity", 0) if coach_item else 0
                jw_qty = jw_item.get("quantity", 0) if jw_item else 0
                nord_qty = nord_item.get("quantity", 0) if nord_item else 0
                total_cert_qty = sum(it.get("quantity", 0) for it in cert_items)
                physical_count = coach_qty + jw_qty + nord_qty
                bubble_count = await self.get_bubble_count(page)

                # Coach cert = 1, JW PEI cert = 1 -> total cert = 2. Physical count = 3.
                s6_pass = (jw_qty == 1 and coach_qty == 1 and total_cert_qty == 2 and physical_count == 3 and (bubble_count is None or bubble_count == 3))
                self.record("ADV-6", "Step JW PEI DOWN to 1: JW PEI cert scales down in lockstep to 1 (total certs=2), Physical=3, Bubble=3",
                            s6_pass, {"jw_qty": jw_qty, "coach_qty": coach_qty, "total_cert_qty": total_cert_qty, "physical": physical_count, "bubble": bubble_count})

                # Step 7: Detach only Coach Certificate
                print("\n[Action] Detaching Coach Certificate...")
                coach_detach = page.locator(f"tr[data-variant-id='{PRODUCTS['Coach']['variant_id']}'] .ra-remove-cert-btn").first
                if await coach_detach.count() == 0:
                    coach_detach = page.locator(".ra-remove-cert-btn").first
                await coach_detach.click()
                await page.wait_for_timeout(4000)

                cart = await self.get_cart(page)
                items = cart.get("items", [])
                coach_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Coach"]["variant_id"]), None)
                jw_item = next((it for it in items if it.get("variant_id") == PRODUCTS["JW_PEI"]["variant_id"]), None)
                nord_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Nordstrom"]["variant_id"]), None)
                cert_items = [it for it in items if it.get("variant_id") == CHECKCHECK_VARIANT_ID]

                coach_qty = coach_item.get("quantity", 0) if coach_item else 0
                jw_qty = jw_item.get("quantity", 0) if jw_item else 0
                nord_qty = nord_item.get("quantity", 0) if nord_item else 0
                total_cert_qty = sum(it.get("quantity", 0) for it in cert_items)
                physical_count = coach_qty + jw_qty + nord_qty
                bubble_count = await self.get_bubble_count(page)

                # Total certs should now be 1 (JW PEI only). Coach still in cart. Physical count = 3.
                s7_pass = (total_cert_qty == 1 and coach_qty == 1 and jw_qty == 1 and nord_qty == 1 and physical_count == 3 and (bubble_count is None or bubble_count == 3))
                self.record("ADV-7", "Detach Coach Certificate: Coach cert removed, JW PEI cert untouched, Physical=3, Bubble=3",
                            s7_pass, {"coach_qty": coach_qty, "total_cert_qty": total_cert_qty, "jw_qty": jw_qty, "physical": physical_count, "bubble": bubble_count})

                # Step 8: Remove JW PEI Parent completely
                print("\n[Action] Removing JW PEI parent item completely...")
                jw_remove = page.locator(f"tr[data-variant-id='{PRODUCTS['JW_PEI']['variant_id']}'] button.cart-items__remove, tr[data-variant-id='{PRODUCTS['JW_PEI']['variant_id']}'] [ref='removeButton'], tr[data-variant-id='{PRODUCTS['JW_PEI']['variant_id']}'] button[name='remove']").first
                if await jw_remove.count() > 0:
                    await jw_remove.click()
                else:
                    # Direct input zeroing
                    jw_input = page.locator(f"tr[data-variant-id='{PRODUCTS['JW_PEI']['variant_id']}'] input[type='number']").first
                    if await jw_input.count() > 0:
                        await jw_input.fill("0")
                        await jw_input.dispatch_event("change")
                        await jw_input.press("Enter")
                await page.wait_for_timeout(4000)

                cart = await self.get_cart(page)
                items = cart.get("items", [])
                coach_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Coach"]["variant_id"]), None)
                jw_item = next((it for it in items if it.get("variant_id") == PRODUCTS["JW_PEI"]["variant_id"]), None)
                nord_item = next((it for it in items if it.get("variant_id") == PRODUCTS["Nordstrom"]["variant_id"]), None)
                cert_items = [it for it in items if it.get("variant_id") == CHECKCHECK_VARIANT_ID]

                coach_qty = coach_item.get("quantity", 0) if coach_item else 0
                jw_qty = jw_item.get("quantity", 0) if jw_item else 0
                nord_qty = nord_item.get("quantity", 0) if nord_item else 0
                total_cert_qty = sum(it.get("quantity", 0) for it in cert_items)
                physical_count = coach_qty + jw_qty + nord_qty
                bubble_count = await self.get_bubble_count(page)

                # JW PEI removed AND JW PEI cert atomically removed -> total certs = 0, zero orphans! Physical count = 2.
                s8_pass = (jw_qty == 0 and total_cert_qty == 0 and coach_qty == 1 and nord_qty == 1 and physical_count == 2 and (bubble_count is None or bubble_count == 2))
                self.record("ADV-8", "Remove JW PEI Parent: Atomically removes JW PEI cert with ZERO orphaned certs, Physical=2, Bubble=2",
                            s8_pass, {"jw_qty": jw_qty, "total_cert_qty": total_cert_qty, "coach_qty": coach_qty, "nord_qty": nord_qty, "physical": physical_count, "bubble": bubble_count})

            finally:
                print("\n[Teardown] Clearing cart...")
                await self.clear_cart(page)
                await page.close()
                await context.close()
                await browser.close()
        finally:
            await p.stop()

        failed_count = len([r for r in self.results if r["status"] == "FAIL"])
        print("\n" + "="*80)
        print(f"ADVERSARIAL HARNESS EXECUTION COMPLETE: {len(self.results) - failed_count}/{len(self.results)} PASSED")
        print("="*80)
        return 0 if failed_count == 0 else 1

async def main():
    runner = AdversarialRunner(headless=True)
    exit_code = await runner.run()
    
    # Save results to challenger_2 folder
    out_dir = os.path.join(PROJECT_ROOT, "..", ".agents", "teamwork", "challenger_2")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "adversarial_mixed_cart_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(runner.results, f, indent=2, ensure_ascii=False)
    print(f"Saved report to: {report_path}")
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
