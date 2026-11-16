#!/usr/bin/env python3
"""
Adversarial Stress Test Harness: Cart Stepper & 1:1 Quantity Synchronization
Author: Challenger 1 (Empirical Challenger)
Target Storefront: https://therareavenue.com (hewmvw-am.myshopify.com)
Active Theme: gid://shopify/OnlineStoreTheme/198751387814 (Horizon 4.3.0, themeStoreId: 2481)
Service Variant: 57721101779110 (₹699.00 / 69900 paise)

Objectives:
1. Rapid sequential stepper clicks (e.g. 1 -> 5 -> 2) under zero-delay hammering
2. Direct keyboard typing into quantity inputs (typing '5', '2', '12', '0')
3. Rapid item removal and zeroing across single-item and multi-item carts
4. Detaching and re-attaching certificates post-cart addition across multiple stores
5. Confirming zero orphaned certificates remain in any state, and cart subtotal strictly matches qty * (product_price + 69900)
"""

import os
import sys
import json
import time
import asyncio
from typing import Dict, Any, List, Optional

# Windows console UTF-8 reconfiguration
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

PRIMARY_STOREFRONT_URL = "https://therareavenue.com"
FALLBACK_STOREFRONT_URL = "https://hewmvw-am.myshopify.com"
CHECKCHECK_VARIANT_ID = 57721101779110
CHECKCHECK_PRICE_INR = 699
CHECKCHECK_PRICE_PAISE = 69900

PARTNER_STORES = {
    "Coach": {
        "handle": "pouch-in-signature-canvas",
        "variant_id": 57530143768742,
        "price_inr": 13599,
        "price_paise": 1359900,
        "name": "Coach Pouch in Signature Canvas"
    },
    "Jomashop": {
        "handle": "tissot-carson-watch-t1224071105100",
        "variant_id": 57514277896358,
        "price_inr": 57099,
        "price_paise": 5709900,
        "name": "Tissot Carson Watch"
    },
    "Michael Kors": {
        "handle": "cherie-leather-sandal",
        "variant_id": 57546840965286,
        "price_inr": 9499,
        "price_paise": 949900,
        "name": "Michael Kors Cherie Leather Sandal"
    },
    "JW PEI": {
        "handle": "hana-large-tote-bag-pink",
        "variant_id": 57534238032038,
        "price_inr": 26699,
        "price_paise": 2669900,
        "name": "JW PEI Hana Large Tote Bag"
    }
}

ARTIFACT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\3851fc2f-0416-4eef-b2dc-f4a095624dcf\challenger_screenshots"
os.makedirs(ARTIFACT_DIR, exist_ok=True)


class AdversarialTestResult:
    def __init__(self, test_id: str, name: str, passed: bool, message: str = "", details: Optional[Dict[str, Any]] = None):
        self.test_id = test_id
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {
            "test_id": self.test_id,
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "message": self.message,
            "details": self.details
        }


class CartStepperAdversarialHarness:
    def __init__(self, headless: bool = True, channel: str = "msedge"):
        self.base_url = PRIMARY_STOREFRONT_URL
        self.fallback_url = FALLBACK_STOREFRONT_URL
        self.active_base_url = self.base_url
        self.headless = headless
        self.channel = channel
        self.results: List[AdversarialTestResult] = []

    async def create_context(self, browser: Browser) -> BrowserContext:
        return await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
            viewport={"width": 1280, "height": 900}
        )

    async def goto_page(self, page: Page, path: str):
        url = f"{self.active_base_url}/{path.lstrip('/')}"
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_load_state("domcontentloaded")
            title = await page.title()
            if "Just a moment..." in title or "challenge" in title.lower():
                self.active_base_url = self.fallback_url
                fallback_target = f"{self.fallback_url}/{path.lstrip('/')}"
                await page.goto(fallback_target, timeout=25000)
                await page.wait_for_load_state("domcontentloaded")
        except Exception:
            self.active_base_url = self.fallback_url
            fallback_target = f"{self.fallback_url}/{path.lstrip('/')}"
            await page.goto(fallback_target, timeout=25000)
            await page.wait_for_load_state("domcontentloaded")

    async def clear_cart(self, page: Page):
        try:
            await page.evaluate("fetch('/cart/clear.js', { method: 'POST', headers: {'Accept': 'application/json'} }).then(r => r.json()).catch(() => ({}))")
            await page.wait_for_timeout(400)
        except Exception:
            pass

    async def get_cart(self, page: Page) -> Dict[str, Any]:
        try:
            data = await page.evaluate("fetch('/cart.js').then(r => r.json())")
            if isinstance(data, dict) and "items" in data:
                return data
        except Exception:
            pass
        return {}

    async def add_via_pdp(self, page: Page, store_key: str, with_checkcheck: bool = True):
        info = PARTNER_STORES[store_key]
        await self.goto_page(page, f"/products/{info['handle']}")
        await page.wait_for_timeout(1000)
        cc_box = page.locator("#checkcheck-addon-checkbox").first
        if await cc_box.count() > 0:
            if with_checkcheck:
                await cc_box.scroll_into_view_if_needed()
                if not await cc_box.is_checked():
                    await cc_box.check()
            else:
                if await cc_box.is_checked():
                    await cc_box.uncheck()

        atc_btn = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await atc_btn.scroll_into_view_if_needed()
        await atc_btn.click()
        await page.wait_for_timeout(3500)

    def record(self, test_id: str, name: str, passed: bool, message: str = "", details: Optional[Dict[str, Any]] = None):
        res = AdversarialTestResult(test_id, name, passed, message, details)
        self.results.append(res)
        tag = "[PASS]" if passed else "[FAIL]"
        print(f" {tag} {test_id}: {name}")
        if not passed:
            print(f"       -> Reason: {message}")
        if details:
            print(f"       -> Details: {details}")

    # =========================================================================
    # ADV-1: Rapid Sequential Stepper Clicks Concurrency (1 -> 5 -> 2)
    # =========================================================================
    async def test_adv1_rapid_sequential_stepper(self, browser: Browser):
        print("\n" + "="*80)
        print("ADV-1: Rapid Sequential Stepper Clicks Concurrency (1 -> 5 -> 2)")
        print("="*80)
        context = await self.create_context(browser)
        page = await context.new_page()
        try:
            await self.clear_cart(page)
            coach = PARTNER_STORES["Coach"]
            await self.add_via_pdp(page, "Coach", with_checkcheck=True)

            await self.goto_page(page, "/cart")
            await page.wait_for_timeout(1000)

            plus_btn = page.locator("button[name='plus']").first
            assert await plus_btn.count() > 0, "Plus button not found"

            print(" [ACTION] Rapid hammer: clicking plus 4 times in quick succession...")
            for _ in range(4):
                await plus_btn.click(delay=50)

            await page.wait_for_timeout(4000)

            cart_step_up = await self.get_cart(page)
            p_up = next((it["quantity"] for it in cart_step_up.get("items", []) if it["variant_id"] == coach["variant_id"]), 0)
            c_up = next((it["quantity"] for it in cart_step_up.get("items", []) if it["variant_id"] == CHECKCHECK_VARIANT_ID), 0)
            total_up = cart_step_up.get("total_price", 0)

            expected_up_subtotal = p_up * (coach["price_paise"] + CHECKCHECK_PRICE_PAISE)
            up_pass = (p_up == c_up and p_up >= 2 and abs(total_up - expected_up_subtotal) <= 100)

            self.record(
                "ADV-1.1", f"Rapid 4x plus clicks step up in lockstep (Product: {p_up}, Cert: {c_up})",
                up_pass,
                f"Desync on rapid step up: Prod={p_up}, Cert={c_up}, Total={total_up}, Expected={expected_up_subtotal}",
                {"product_qty": p_up, "cert_qty": c_up, "total_price": total_up}
            )

            minus_btn = page.locator("button[name='minus']").first
            assert await minus_btn.count() > 0, "Minus button not found"

            clicks_down = min(3, p_up - 1)
            print(f" [ACTION] Rapid hammer: clicking minus {clicks_down} times in quick succession...")
            for _ in range(clicks_down):
                await minus_btn.click(delay=50)

            await page.wait_for_timeout(4000)

            cart_step_down = await self.get_cart(page)
            p_down = next((it["quantity"] for it in cart_step_down.get("items", []) if it["variant_id"] == coach["variant_id"]), 0)
            c_down = next((it["quantity"] for it in cart_step_down.get("items", []) if it["variant_id"] == CHECKCHECK_VARIANT_ID), 0)
            total_down = cart_step_down.get("total_price", 0)
            expected_down_subtotal = p_down * (coach["price_paise"] + CHECKCHECK_PRICE_PAISE)

            down_pass = (p_down == c_down and p_down > 0 and abs(total_down - expected_down_subtotal) <= 100)

            shot_path = os.path.join(ARTIFACT_DIR, "adv1_stepper_rapid.png")
            await page.screenshot(path=shot_path)

            self.record(
                "ADV-1.2", f"Rapid decrement steps down in lockstep with zero orphan (Product: {p_down}, Cert: {c_down})",
                down_pass,
                f"Desync on rapid step down: Prod={p_down}, Cert={c_down}, Total={total_down}, Expected={expected_down_subtotal}",
                {"product_qty": p_down, "cert_qty": c_down, "total_price": total_down, "screenshot": shot_path}
            )

        finally:
            await self.clear_cart(page)
            await page.close()
            await context.close()

    # =========================================================================
    # ADV-2: Direct Keyboard Typing into Quantity Inputs ('5', '2', '12', '0')
    # =========================================================================
    async def test_adv2_keyboard_typing_sync(self, browser: Browser):
        print("\n" + "="*80)
        print("ADV-2: Direct Keyboard Typing into Quantity Inputs ('5', '2', '12', '0')")
        print("="*80)
        context = await self.create_context(browser)
        page = await context.new_page()
        try:
            await self.clear_cart(page)
            coach = PARTNER_STORES["Coach"]
            await self.add_via_pdp(page, "Coach", with_checkcheck=True)

            await self.goto_page(page, "/cart")
            await page.wait_for_timeout(1000)

            # Case ADV-2.1: Direct type '5'
            print(" [ACTION] Typing '5' into quantity input...")
            qty_input = page.locator("input[name='updates[]'], .quantity-selector input[type='number'], input.quantity__input").first
            await qty_input.scroll_into_view_if_needed()
            await qty_input.fill("5")
            await qty_input.dispatch_event("change")
            await qty_input.blur()
            await page.wait_for_timeout(4000)

            cart_k5 = await self.get_cart(page)
            p_5 = next((it["quantity"] for it in cart_k5.get("items", []) if it["variant_id"] == coach["variant_id"]), 0)
            c_5 = next((it["quantity"] for it in cart_k5.get("items", []) if it["variant_id"] == CHECKCHECK_VARIANT_ID), 0)
            tot_5 = cart_k5.get("total_price", 0)
            exp_5 = 5 * (coach["price_paise"] + CHECKCHECK_PRICE_PAISE)
            pass_k5 = (p_5 == 5 and c_5 == 5 and abs(tot_5 - exp_5) <= 100)

            self.record(
                "ADV-2.1", f"Direct keyboard typing '5' synchronizes cert to 5 (Prod: {p_5}, Cert: {c_5})",
                pass_k5,
                f"Desync on typing '5': Prod={p_5}, Cert={c_5}, Tot={tot_5}, Exp={exp_5}",
                {"product_qty": p_5, "cert_qty": c_5, "total_price": tot_5}
            )

            # Case ADV-2.2: Direct type '2'
            print(" [ACTION] Typing '2' into quantity input...")
            await qty_input.fill("2")
            await qty_input.dispatch_event("change")
            await qty_input.blur()
            await page.wait_for_timeout(4000)

            cart_k2 = await self.get_cart(page)
            p_2 = next((it["quantity"] for it in cart_k2.get("items", []) if it["variant_id"] == coach["variant_id"]), 0)
            c_2 = next((it["quantity"] for it in cart_k2.get("items", []) if it["variant_id"] == CHECKCHECK_VARIANT_ID), 0)
            tot_2 = cart_k2.get("total_price", 0)
            exp_2 = 2 * (coach["price_paise"] + CHECKCHECK_PRICE_PAISE)
            pass_k2 = (p_2 == 2 and c_2 == 2 and abs(tot_2 - exp_2) <= 100)

            self.record(
                "ADV-2.2", f"Direct keyboard typing '2' scales cert down to 2 (Prod: {p_2}, Cert: {c_2})",
                pass_k2,
                f"Desync on typing '2': Prod={p_2}, Cert={c_2}, Tot={tot_2}, Exp={exp_2}",
                {"product_qty": p_2, "cert_qty": c_2, "total_price": tot_2}
            )

            # Case ADV-2.3: Boundary high quantity '12'
            print(" [ACTION] Typing high quantity '12' into quantity input...")
            await qty_input.fill("12")
            await qty_input.dispatch_event("change")
            await qty_input.blur()
            await page.wait_for_timeout(4000)

            cart_k12 = await self.get_cart(page)
            p_12 = next((it["quantity"] for it in cart_k12.get("items", []) if it["variant_id"] == coach["variant_id"]), 0)
            c_12 = next((it["quantity"] for it in cart_k12.get("items", []) if it["variant_id"] == CHECKCHECK_VARIANT_ID), 0)
            tot_12 = cart_k12.get("total_price", 0)
            exp_12 = 12 * (coach["price_paise"] + CHECKCHECK_PRICE_PAISE)
            pass_k12 = (p_12 == 12 and c_12 == 12 and abs(tot_12 - exp_12) <= 100)

            self.record(
                "ADV-2.3", f"Boundary high quantity typing '12' synchronizes cert to 12 (Prod: {p_12}, Cert: {c_12})",
                pass_k12,
                f"Desync on typing '12': Prod={p_12}, Cert={c_12}, Tot={tot_12}, Exp={exp_12}",
                {"product_qty": p_12, "cert_qty": c_12, "total_price": tot_12}
            )

            # Case ADV-2.4: Direct zeroing via typing '0'
            print(" [ACTION] Typing '0' to trigger atomic zeroing...")
            await qty_input.fill("0")
            await qty_input.dispatch_event("change")
            await qty_input.blur()
            await page.wait_for_timeout(4000)

            cart_k0 = await self.get_cart(page)
            items_k0 = cart_k0.get("items", [])
            has_orphaned = any(it["variant_id"] == CHECKCHECK_VARIANT_ID for it in items_k0)
            has_coach = any(it["variant_id"] == coach["variant_id"] for it in items_k0)
            pass_k0 = (len(items_k0) == 0) or (not has_orphaned and not has_coach)

            shot_path = os.path.join(ARTIFACT_DIR, "adv2_keyboard_zero.png")
            await page.screenshot(path=shot_path)

            self.record(
                "ADV-2.4", "Direct keyboard typing '0' atomically zeros parent and certificate (0 orphans)",
                pass_k0,
                f"Cart failed to zero on typing '0': items count={len(items_k0)}, orphaned_cert={has_orphaned}",
                {"remaining_items": len(items_k0), "has_orphaned": has_orphaned, "screenshot": shot_path}
            )

        finally:
            await self.clear_cart(page)
            await page.close()
            await context.close()

    # =========================================================================
    # ADV-3: Rapid Item Removal and Atomic Zeroing Invariant
    # =========================================================================
    async def test_adv3_rapid_removal_and_zeroing(self, browser: Browser):
        print("\n" + "="*80)
        print("ADV-3: Rapid Item Removal and Atomic Zeroing Invariant")
        print("="*80)
        context = await self.create_context(browser)
        page = await context.new_page()
        try:
            # Subtest 3.1: Single item cart removal
            await self.clear_cart(page)
            coach = PARTNER_STORES["Coach"]
            await self.add_via_pdp(page, "Coach", with_checkcheck=True)

            await self.goto_page(page, "/cart")
            await page.wait_for_timeout(1000)

            remove_btn = page.locator("button.cart-items__remove").first
            assert await remove_btn.count() > 0, "Parent remove button missing"

            print(" [ACTION] Clicking parent item remove button...")
            await remove_btn.click()
            await page.wait_for_timeout(4000)

            cart_rem1 = await self.get_cart(page)
            items_rem1 = cart_rem1.get("items", [])
            has_orphaned1 = any(it["variant_id"] == CHECKCHECK_VARIANT_ID for it in items_rem1)
            pass_rem1 = (len(items_rem1) == 0 and not has_orphaned1)

            self.record(
                "ADV-3.1", "Single certified item removal leaves cart completely empty with 0 orphaned certificates",
                pass_rem1,
                f"Cart not empty after removal: items={len(items_rem1)}, orphaned={has_orphaned1}",
                {"remaining_items": len(items_rem1), "orphaned": has_orphaned1}
            )

            # Subtest 3.2: Multi-item cart partial removal
            print(" [ACTION] Populating multi-item cart: Coach Pouch (certified) + MK Sandal (certified)...")
            mk = PARTNER_STORES["Michael Kors"]
            await self.add_via_pdp(page, "Coach", with_checkcheck=True)
            await self.add_via_pdp(page, "Michael Kors", with_checkcheck=True)

            await self.goto_page(page, "/cart")
            await page.wait_for_timeout(1000)

            # Remove Coach row
            coach_row_remove = page.locator(f"tr[data-variant-id='{coach['variant_id']}'] button.cart-items__remove").first
            assert await coach_row_remove.count() > 0, "Coach remove button missing"
            await coach_row_remove.click()
            await page.wait_for_timeout(4000)

            cart_multi = await self.get_cart(page)
            items_multi = cart_multi.get("items", [])
            has_coach_rem = any(it["variant_id"] == coach["variant_id"] for it in items_multi)
            mk_item = next((it for it in items_multi if it["variant_id"] == mk["variant_id"]), None)
            mk_certs = [it for it in items_multi if it["variant_id"] == CHECKCHECK_VARIANT_ID]

            coach_cert_gone = not any(it.get("properties", {}).get("_parent_id") == str(coach["variant_id"]) for it in mk_certs)
            mk_cert_intact = len(mk_certs) == 1 and mk_item is not None and mk_item["quantity"] == 1

            pass_rem2 = (not has_coach_rem and coach_cert_gone and mk_cert_intact)

            shot_path = os.path.join(ARTIFACT_DIR, "adv3_multi_removal.png")
            await page.screenshot(path=shot_path)

            self.record(
                "ADV-3.2", "Multi-item cart: removing one certified product removes its cert while preserving second item & its cert",
                pass_rem2,
                f"Multi-item removal desync: coach_rem={not has_coach_rem}, coach_cert_gone={coach_cert_gone}, mk_cert_intact={mk_cert_intact}",
                {"remaining_items": len(items_multi), "cert_count": len(mk_certs), "screenshot": shot_path}
            )

        finally:
            await self.clear_cart(page)
            await page.close()
            await context.close()

    # =========================================================================
    # ADV-4: Detaching and Re-Attaching Certificates Post-Cart Addition
    # =========================================================================
    async def test_adv4_detach_and_reattach_cycles(self, browser: Browser):
        print("\n" + "="*80)
        print("ADV-4: Detaching and Re-Attaching Certificates Post-Cart Addition")
        print("="*80)
        context = await self.create_context(browser)
        page = await context.new_page()
        try:
            await self.clear_cart(page)
            jw = PARTNER_STORES["JW PEI"]
            await self.add_via_pdp(page, "JW PEI", with_checkcheck=False)

            await self.goto_page(page, "/cart")
            await page.wait_for_timeout(1000)

            # Step 1: In-cart add certificate button
            add_cert_btn = page.locator(".ra-add-cert-btn").first
            assert await add_cert_btn.count() > 0, "In-cart '+ Add CheckCheck Certificate' button not rendered"

            print(" [ACTION] Clicking in-cart '+ Add CheckCheck Certificate' button...")
            await add_cert_btn.click()
            await page.wait_for_timeout(3500)

            cart_c1 = await self.get_cart(page)
            has_cert_c1 = any(it["variant_id"] == CHECKCHECK_VARIANT_ID for it in cart_c1.get("items", []))
            tot_c1 = cart_c1.get("total_price", 0)
            exp_c1 = jw["price_paise"] + CHECKCHECK_PRICE_PAISE
            pass_c1 = (has_cert_c1 and abs(tot_c1 - exp_c1) <= 100)

            self.record(
                "ADV-4.1", "In-cart '+ Add CheckCheck Certificate' adds certificate variant with exact +₹699 subtotal delta",
                pass_c1,
                f"Failed in-cart add: has_cert={has_cert_c1}, tot={tot_c1}, exp={exp_c1}",
                {"has_cert": has_cert_c1, "total_price": tot_c1}
            )

            # Step 2: Step product up to quantity 3
            print(" [ACTION] Stepping product up to quantity 3...")
            plus_btn = page.locator("button[name='plus']").first
            await plus_btn.click()
            await page.wait_for_timeout(3500)
            await plus_btn.click()
            await page.wait_for_timeout(3500)

            cart_c2 = await self.get_cart(page)
            p_c2 = next((it["quantity"] for it in cart_c2.get("items", []) if it["variant_id"] == jw["variant_id"]), 0)
            c_c2 = next((it["quantity"] for it in cart_c2.get("items", []) if it["variant_id"] == CHECKCHECK_VARIANT_ID), 0)
            pass_c2 = (p_c2 == 3 and c_c2 == 3)

            self.record(
                "ADV-4.2", f"Post-cart added certificate scales in lockstep to quantity 3 (Prod: {p_c2}, Cert: {c_c2})",
                pass_c2,
                f"Desync on scaling post-added cert: Prod={p_c2}, Cert={c_c2}",
                {"product_qty": p_c2, "cert_qty": c_c2}
            )

            # Step 3: Detach certificate via .ra-remove-cert-btn
            print(" [ACTION] Detaching certificate via badge [Remove] button...")
            remove_cert_btn = page.locator(".ra-remove-cert-btn").first
            assert await remove_cert_btn.count() > 0, "Badge [Remove] button missing"
            await remove_cert_btn.click()
            await page.wait_for_timeout(3500)

            cart_c3 = await self.get_cart(page)
            items_c3 = cart_c3.get("items", [])
            has_no_cert = not any(it["variant_id"] == CHECKCHECK_VARIANT_ID for it in items_c3)
            p_c3 = next((it["quantity"] for it in items_c3 if it["variant_id"] == jw["variant_id"]), 0)
            tot_c3 = cart_c3.get("total_price", 0)
            exp_c3 = 3 * jw["price_paise"]
            pass_c3 = (has_no_cert and p_c3 == 3 and abs(tot_c3 - exp_c3) <= 100)

            self.record(
                "ADV-4.3", f"Detaching certificate removes all 3 certificates while keeping parent product at quantity 3",
                pass_c3,
                f"Detach failed: has_no_cert={has_no_cert}, prod_qty={p_c3}, tot={tot_c3}, exp={exp_c3}",
                {"has_no_cert": has_no_cert, "product_qty": p_c3, "total_price": tot_c3}
            )

            # Step 4: Re-attach certificate post-detach
            print(" [ACTION] Re-attaching certificate post-detachment...")
            await self.goto_page(page, "/cart")
            await page.wait_for_timeout(1000)
            re_add_btn = page.locator(".ra-add-cert-btn").first
            assert await re_add_btn.count() > 0, "Prompt '+ Add CheckCheck Certificate' not restored"
            await re_add_btn.click()
            await page.wait_for_timeout(3500)

            cart_c4 = await self.get_cart(page)
            p_c4 = next((it["quantity"] for it in cart_c4.get("items", []) if it["variant_id"] == jw["variant_id"]), 0)
            c_c4 = next((it["quantity"] for it in cart_c4.get("items", []) if it["variant_id"] == CHECKCHECK_VARIANT_ID), 0)
            tot_c4 = cart_c4.get("total_price", 0)
            exp_c4 = 3 * (jw["price_paise"] + CHECKCHECK_PRICE_PAISE)
            pass_c4 = (p_c4 == 3 and c_c4 == 3 and abs(tot_c4 - exp_c4) <= 100)

            shot_path = os.path.join(ARTIFACT_DIR, "adv4_reattach_qty3.png")
            await page.screenshot(path=shot_path)

            self.record(
                "ADV-4.4", f"Re-attaching certificate binds exactly 3 certificates matching parent quantity (Prod: {p_c4}, Cert: {c_c4})",
                pass_c4,
                f"Re-attach desync: Prod={p_c4}, Cert={c_c4}, Tot={tot_c4}, Exp={exp_c4}",
                {"product_qty": p_c4, "cert_qty": c_c4, "total_price": tot_c4, "screenshot": shot_path}
            )

        finally:
            await self.clear_cart(page)
            await page.close()
            await context.close()

    # =========================================================================
    # ADV-5: Subtotal Strict Invariant & Zero-Orphan Across Multi-Brand Cart
    # =========================================================================
    async def test_adv5_subtotal_invariant_and_zero_orphans(self, browser: Browser):
        print("\n" + "="*80)
        print("ADV-5: Subtotal Strict Invariant & Zero-Orphan Across Multi-Brand Cart")
        print("="*80)
        context = await self.create_context(browser)
        page = await context.new_page()
        try:
            await self.clear_cart(page)
            coach = PARTNER_STORES["Coach"]
            joma = PARTNER_STORES["Jomashop"]
            mk = PARTNER_STORES["Michael Kors"]

            # Add Coach (certified), Jomashop (uncertified), MK (certified)
            await self.add_via_pdp(page, "Coach", with_checkcheck=True)
            await self.add_via_pdp(page, "Jomashop", with_checkcheck=False)
            await self.add_via_pdp(page, "Michael Kors", with_checkcheck=True)

            await self.goto_page(page, "/cart")
            await page.wait_for_timeout(1000)

            # Step Coach up to 2
            coach_plus = page.locator(f"tr[data-variant-id='{coach['variant_id']}'] button[name='plus']").first
            if await coach_plus.count() > 0:
                await coach_plus.click()
                await page.wait_for_timeout(3500)

            # Step MK up to 3
            mk_plus = page.locator(f"tr[data-variant-id='{mk['variant_id']}'] button[name='plus']").first
            if await mk_plus.count() > 0:
                await mk_plus.click()
                await page.wait_for_timeout(3500)
                await mk_plus.click()
                await page.wait_for_timeout(3500)

            cart_inv = await self.get_cart(page)
            items_inv = cart_inv.get("items", [])

            p_coach = next((it["quantity"] for it in items_inv if it["variant_id"] == coach["variant_id"]), 0)
            p_joma = next((it["quantity"] for it in items_inv if it["variant_id"] == joma["variant_id"]), 0)
            p_mk = next((it["quantity"] for it in items_inv if it["variant_id"] == mk["variant_id"]), 0)

            total_cert_qty = sum(it["quantity"] for it in items_inv if it["variant_id"] == CHECKCHECK_VARIANT_ID)
            expected_cert_qty = p_coach + p_mk  # Jomashop is uncertified

            certs_pass = (total_cert_qty == expected_cert_qty and p_coach == 2 and p_mk == 3 and p_joma == 1)

            self.record(
                "ADV-5.1", f"Multi-brand cart certificates strictly match sum of certified parents (Expected: 5, Got: {total_cert_qty})",
                certs_pass,
                f"Certificate count mismatch: Got={total_cert_qty}, Expected={expected_cert_qty} (Coach={p_coach}, MK={p_mk}, Joma={p_joma})",
                {"coach_qty": p_coach, "mk_qty": p_mk, "joma_qty": p_joma, "total_cert_qty": total_cert_qty}
            )

            # Strict subtotal mathematical verification
            actual_total = cart_inv.get("total_price", 0)
            expected_total = (
                p_coach * (coach["price_paise"] + CHECKCHECK_PRICE_PAISE) +
                p_joma * joma["price_paise"] +
                p_mk * (mk["price_paise"] + CHECKCHECK_PRICE_PAISE)
            )

            diff = abs(actual_total - expected_total)
            subtotal_pass = (diff <= 100)

            shot_path = os.path.join(ARTIFACT_DIR, "adv5_subtotal_invariant.png")
            await page.screenshot(path=shot_path)

            self.record(
                "ADV-5.2", f"Cart subtotal strictly matches mathematical formula sum(qty * (price + cert_fee)) (Diff: {diff/100:.2f} INR)",
                subtotal_pass,
                f"Subtotal drift: Actual={actual_total/100:.2f} INR, Expected={expected_total/100:.2f} INR, Diff={diff/100:.2f}",
                {"actual_paise": actual_total, "expected_paise": expected_total, "diff_paise": diff, "screenshot": shot_path}
            )

            # Now completely remove MK
            mk_remove = page.locator(f"tr[data-variant-id='{mk['variant_id']}'] button.cart-items__remove").first
            if await mk_remove.count() > 0:
                await mk_remove.click()
                await page.wait_for_timeout(4000)

            cart_post_rm = await self.get_cart(page)
            items_post_rm = cart_post_rm.get("items", [])
            total_cert_post_rm = sum(it["quantity"] for it in items_post_rm if it["variant_id"] == CHECKCHECK_VARIANT_ID)
            pass_orphan_check = (total_cert_post_rm == p_coach)  # Only Coach certs should remain

            self.record(
                "ADV-5.3", f"Zero orphaned certificates remain after removing 3-quantity certified item (Remaining certs: {total_cert_post_rm})",
                pass_orphan_check,
                f"Orphaned certificates left: Expected {p_coach}, Got {total_cert_post_rm}",
                {"remaining_certs": total_cert_post_rm, "expected_certs": p_coach}
            )

        finally:
            await self.clear_cart(page)
            await page.close()
            await context.close()

    # =========================================================================
    # SUITE EXECUTION
    # =========================================================================
    async def run_all(self) -> int:
        print("\n" + "="*80)
        print("THE RARE AVENUE - CART STEPPER ADVERSARIAL STRESS HARNESS")
        print(f"Target: {self.base_url}")
        print(f"Browser Channel: {self.channel} (Headless: {self.headless})")
        print("="*80)

        t0 = time.time()
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(channel=self.channel, headless=self.headless)
            except Exception:
                browser = await p.chromium.launch(headless=self.headless)

            try:
                await self.test_adv1_rapid_sequential_stepper(browser)
                await self.test_adv2_keyboard_typing_sync(browser)
                await self.test_adv3_rapid_removal_and_zeroing(browser)
                await self.test_adv4_detach_and_reattach_cycles(browser)
                await self.test_adv5_subtotal_invariant_and_zero_orphans(browser)
            finally:
                await browser.close()

        duration = time.time() - t0
        passed = [r for r in self.results if r.passed]
        failed = [r for r in self.results if not r.passed]

        print("\n" + "="*80)
        print("ADVERSARIAL STRESS HARNESS EXECUTION SUMMARY")
        print("="*80)
        print(f"Total Adversarial Tests : {len(self.results)}")
        print(f"Passed                  : {len(passed)} ({len(passed)/len(self.results)*100:.1f}%)")
        print(f"Failed                  : {len(failed)}")
        print(f"Total Duration          : {duration:.2f}s")
        print("="*80)

        report_path = os.path.join(ARTIFACT_DIR, "adversarial_stress_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "total": len(self.results),
                "passed": len(passed),
                "failed": len(failed),
                "tests": [r.to_dict() for r in self.results]
            }, f, indent=2)
        print(f"Saved adversarial stress JSON report: {report_path}")

        return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    harness = CartStepperAdversarialHarness(headless=True, channel="msedge")
    exit_code = asyncio.run(harness.run_all())
    sys.exit(exit_code)
