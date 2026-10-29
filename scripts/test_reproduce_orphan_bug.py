import asyncio
from playwright.async_api import async_playwright

async def test_orphan_simulation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Navigating to store...")
        await page.goto("https://therareavenue.com/cart")
        await page.wait_for_timeout(2000)

        # Clear cart first
        await page.evaluate("""async () => {
            await fetch('/cart/clear.js', { method: 'POST' });
        }""")
        print("Cart cleared.")

        # Simulate adding 4 orphan certificates (no properties)
        await page.evaluate("""async () => {
            for (let i = 0; i < 4; i++) {
                await fetch('/cart/add.js', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items: [{ id: 57721101779110, quantity: 1 }] })
                });
            }
        }""")
        print("Added 4 orphan certificates.")

        # Add 1 Versace watch (or any watch) with attached certificate
        # Versace watch variant: 57529432605030 (let's check variant id for Versace Greca Sphere)
        # Let's add with properties
        await page.evaluate("""async () => {
            await fetch('/cart/add.js', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    items: [
                        {
                            id: 57529432605030,
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
                                '_parent_id': '57529432605030'
                            }
                        }
                    ]
                })
            });
        }""")
        print("Added watch with attached certificate.")

        # Inspect cart.js
        cart = await page.evaluate("async () => { const res = await fetch('/cart.js'); return await res.json(); }")
        print(f"Cart total items: {cart['item_count']}, total price: {cart['total_price'] / 100}")
        print("Line items in cart:")
        for idx, it in enumerate(cart['items']):
            print(f"  {idx+1}. {it['title']} (variant {it['variant_id']}) x {it['quantity']} - Props: {it.get('properties')}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_orphan_simulation())
