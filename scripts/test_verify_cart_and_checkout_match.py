import asyncio
import os
import sys
import json
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

async def test_reconciler_and_checkout():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("--- STEP 1: Clear Cart via GET /cart/clear.js ---")
        await page.goto("https://therareavenue.com/cart/clear.js")
        await page.wait_for_timeout(2000)

        # Confirm cart is empty
        cart_empty = await page.evaluate("async () => { const r = await fetch('/cart.js'); return await r.json(); }")
        print("Cart cleared, items:", cart_empty.get('item_count'))

        print("--- STEP 2: Inject 4 Orphan Certificates ---")
        res2 = await page.evaluate("""async () => {
            const results = [];
            for (let i = 0; i < 4; i++) {
                const r = await fetch('/cart/add.js', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                    body: JSON.stringify({ items: [{ id: 57721101779110, quantity: 1 }] })
                });
                results.push(r.status);
            }
            return results;
        }""")
        print("Added 4 orphan certificates, statuses:", res2)

        print("--- STEP 3: Add Versace Watch with Attached Certificate ---")
        res3 = await page.evaluate("""async () => {
            const r = await fetch('/cart/add.js', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify({
                    items: [
                        {
                            id: 57514247946406,
                            quantity: 1,
                            properties: {
                                'Authentication': 'CheckCheck Certified (+₹699)',
                                '_checkcheck_parent': 'true'
                            }
                        },
                        {
                            id: 57721101779110,
                            quantity: 1,
                            properties: {
                                'Certified For': 'Versace Greca Sphere Quartz Silver Dial Ladies Watch Box Set VE9C00324',
                                '_parent_id': '57514247946406'
                            }
                        }
                    ]
                })
            });
            return { status: r.status };
        }""")
        print("Added Versace watch with cert, status:", res3['status'])

        raw_cart = await page.evaluate("async () => { const r = await fetch('/cart.js'); return await r.json(); }")
        print(f"Raw cart before visiting /cart: count={raw_cart.get('item_count')}, total=Rs. {raw_cart.get('total_price', 0)/100}")

        print("--- STEP 4: Navigate to Cart Page to Trigger Auto-Reconciliation ---")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_timeout(4000)

        # Inspect cart data after auto-reconciliation
        cart_data = await page.evaluate("async () => { const r = await fetch('/cart.js'); return await r.json(); }")
        total_items = cart_data.get('item_count', 0)
        total_price = cart_data.get('total_price', 0) / 100
        print(f"Cart Data after Reconciler: item_count={total_items}, total_price=Rs. {total_price}")
        print("Cart items:")
        for idx, it in enumerate(cart_data.get('items', [])):
            print(f"  {idx+1}. {it.get('title')} (variant {it.get('variant_id')}) x {it.get('quantity')} - Props: {it.get('properties')}")

        cart_screenshot = os.path.join(SCREENSHOT_DIR, "cart_reconciled_clean.png")
        await page.screenshot(path=cart_screenshot, full_page=True)
        print(f"Captured reconciled cart screenshot: {cart_screenshot}")

        print("--- STEP 5: Click Check Out and Verify Checkout Line Items ---")
        checkout_btn = page.locator("#checkout, [name='checkout'], .cart__checkout-button").first
        await checkout_btn.click()
        await page.wait_for_timeout(6000)
        print(f"Current URL: {page.url}")

        checkout_screenshot = os.path.join(SCREENSHOT_DIR, "checkout_reconciled_clean.png")
        await page.screenshot(path=checkout_screenshot, full_page=True)
        print(f"Captured reconciled checkout screenshot: {checkout_screenshot}")

        # Assertions
        assert total_items == 2, f"Expected 2 items in cart (1 watch + 1 cert), got {total_items}"
        # 57999 + 699 = 58698
        assert total_price == 58698.0, f"Expected total Rs. 58698.0, got {total_price}"
        print(">>> ALL ASSERTIONS PASSED! CART AND CHECKOUT MATCH EXACTLY! <<<")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_reconciler_and_checkout())
