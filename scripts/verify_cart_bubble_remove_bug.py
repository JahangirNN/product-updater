#!/usr/bin/env python3
"""
Empirical Bug Reproduction Harness: Cart Bubble Desync on Certified Parent Removal
Target Storefront: https://therareavenue.com
"""

import sys
import os
import json
import time
import asyncio

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.async_api import async_playwright

STOREFRONT_URL = "https://therareavenue.com"

async def run_reproduction():
    print("="*80)
    print("STARTING EMPIRICAL REPRODUCTION: Cart Bubble Desync on Certified Parent Removal")
    print("="*80)

    p = await async_playwright().start()
    browser = None
    page = None
    context = None
    try:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Step 1: Clear Cart
        print("\n1. Clearing cart...")
        await page.goto(f"{STOREFRONT_URL}/cart", timeout=25000)
        await page.evaluate("fetch('/cart/clear.js', {method: 'POST'})")
        await page.wait_for_timeout(1000)

        # Step 2: Add Coach WITH cert (Variant 57530143768742)
        print("2. Adding Coach with CheckCheck...")
        await page.goto(f"{STOREFRONT_URL}/products/pouch-in-signature-canvas", timeout=25000)
        await page.wait_for_load_state("domcontentloaded")
        box = page.locator("#checkcheck-addon-checkbox").first
        if await box.count() > 0 and not await box.is_checked():
            await box.check()
        atc = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await atc.click()
        await page.wait_for_timeout(3500)

        # Step 3: Add JW PEI WITHOUT cert (Variant 57534238032038)
        print("3. Adding JW PEI without CheckCheck...")
        await page.goto(f"{STOREFRONT_URL}/products/hana-large-tote-bag-pink", timeout=25000)
        await page.wait_for_load_state("domcontentloaded")
        box = page.locator("#checkcheck-addon-checkbox").first
        if await box.count() > 0 and await box.is_checked():
            await box.uncheck()
        atc = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await atc.click()
        await page.wait_for_timeout(3500)

        # Step 4: Add Nordstrom WITHOUT cert (Variant 57582236237990)
        print("4. Adding Nordstrom without CheckCheck...")
        await page.goto(f"{STOREFRONT_URL}/products/w-clifton-11-gtx-glm", timeout=25000)
        await page.wait_for_load_state("domcontentloaded")
        box = page.locator("#checkcheck-addon-checkbox").first
        if await box.count() > 0 and await box.is_checked():
            await box.uncheck()
        atc = page.locator("product-form-component button[type='submit'], .product-form-buttons button[name='add']").first
        await atc.click()
        await page.wait_for_timeout(3500)

        # Step 5: Go to /cart
        print("5. Navigating to /cart...")
        await page.goto(f"{STOREFRONT_URL}/cart", timeout=25000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)

        cart_data = await page.evaluate("fetch('/cart.js').then(r => r.json())")
        phys_items = [it for it in cart_data.get("items", []) if it.get("variant_id") != 57721101779110]
        phys_qty = sum(it.get("quantity", 0) for it in phys_items)
        bubble_text = (await page.locator("[ref='cartBubbleCount']").inner_text()).strip()
        session_store = await page.evaluate("sessionStorage.getItem('cart-count')")
        print(f"   Pre-upgrade Cart: Physical items = {phys_qty}, Bubble text = '{bubble_text}', sessionStorage = '{session_store}'")

        # Step 6: In-Cart Upgrade JW PEI (Attach cert)
        print("6. In-cart upgrade of JW PEI (clicking .ra-add-cert-btn)...")
        jw_row = page.locator("tr[data-variant-id='57534238032038']").first
        add_btn = jw_row.locator(".ra-add-cert-btn").first
        await add_btn.click()
        await page.wait_for_timeout(4000)

        cart_data = await page.evaluate("fetch('/cart.js').then(r => r.json())")
        phys_items = [it for it in cart_data.get("items", []) if it.get("variant_id") != 57721101779110]
        phys_qty = sum(it.get("quantity", 0) for it in phys_items)
        bubble_text = (await page.locator("[ref='cartBubbleCount']").inner_text()).strip()
        session_store = await page.evaluate("sessionStorage.getItem('cart-count')")
        print(f"   Post-upgrade Cart: Physical items = {phys_qty}, Bubble text = '{bubble_text}', sessionStorage = '{session_store}'")

        # Step 7: Click remove on JW PEI
        # Note: Because JW PEI has attached cert, its remove button has onclick="removeProductAndCert(...)"
        print("7. Clicking remove on JW PEI (which has attached cert)...")
        jw_row = page.locator("tr[data-variant-id='57534238032038']").first
        remove_btn = jw_row.locator("button.cart-items__remove").first
        onclick_attr = await remove_btn.get_attribute("onclick")
        print(f"   JW PEI remove button onclick attribute: {onclick_attr}")

        await remove_btn.click()
        # Wait for reload
        await page.wait_for_timeout(5000)

        cart_data = await page.evaluate("fetch('/cart.js').then(r => r.json())")
        phys_items = [it for it in cart_data.get("items", []) if it.get("variant_id") != 57721101779110]
        phys_qty = sum(it.get("quantity", 0) for it in phys_items)
        bubble_text = (await page.locator("[ref='cartBubbleCount']").inner_text()).strip()
        session_store = await page.evaluate("sessionStorage.getItem('cart-count')")

        print("\n" + "="*80)
        print("EMPIRICAL OBSERVATION POST-REMOVAL:")
        print(f"   Authoritative Backend Cart Physical Items Count : {phys_qty}")
        print(f"   Remaining Physical Items in Cart               : {[it.get('title') for it in phys_items]}")
        print(f"   DOM Header Cart Bubble Count Displayed         : '{bubble_text}'")
        print(f"   Browser sessionStorage['cart-count'] Value      : '{session_store}'")
        print("="*80)

        if str(phys_qty) != bubble_text:
            print(f"\n[CONFIRMED BUG DETECTED]: Desynchronization between Backend ({phys_qty}) and Cart Bubble ('{bubble_text}')!")
            print("ROOT CAUSE: removeProductAndCert() reloads the page via window.location.reload() without updating sessionStorage['cart-count'].")
            print("On reload, ensureCartBubbleIsCorrect() in cart-icon.js sees stale sessionStorage ('3') within 10s and overwrites the server-rendered '2'!")
            return 1
        else:
            print("\n[NO BUG]: Cart bubble correctly matches backend.")
            return 0

    finally:
        if page:
            try:
                await page.evaluate("fetch('/cart/clear.js', {method: 'POST'})")
                await page.close()
            except Exception:
                pass
        if context:
            await context.close()
        if browser:
            await browser.close()
        await p.stop()

if __name__ == "__main__":
    code = asyncio.run(run_reproduction())
    sys.exit(code)
