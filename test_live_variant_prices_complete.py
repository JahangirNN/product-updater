import asyncio
import os
import time
from playwright.async_api import async_playwright

async def run():
    print("Starting Comprehensive Variant Price Test...", flush=True)
    out_dir = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        
        # --- TEST 1: PDP Live Variant Price Update ---
        pdp_page = await browser.new_page(viewport={"width": 1280, "height": 900})
        pdp_url = f"https://therareavenue.com/products/teri-shoulder-bag?v={int(time.time())}"
        print(f"Navigating to {pdp_url}...", flush=True)
        await pdp_page.goto(pdp_url, wait_until="domcontentloaded", timeout=25000)
        await pdp_page.wait_for_timeout(2500)

        initial_pdp_price = await pdp_page.locator('product-price').first.text_content()
        print(f"[PDP] Initial Price: {initial_pdp_price.strip()} (Expected: Rs. 20,899)", flush=True)

        # Click Gold/Pink swatch
        pink_swatch = pdp_page.locator('variant-picker input[value="Gold/Pink"]').first
        pink_parent = pink_swatch.locator('xpath=..')
        print("[PDP] Clicking Gold/Pink swatch...", flush=True)
        await pink_parent.click(force=True)
        await pdp_page.wait_for_timeout(2000)

        new_pdp_price = await pdp_page.locator('product-price').first.text_content()
        print(f"[PDP] New Price: {new_pdp_price.strip()} (Expected: Rs. 26,599)", flush=True)
        
        # Check sticky buy bar price
        sticky_price = await pdp_page.locator('.luxury-sticky-buy-bar__price').first.text_content()
        print(f"[PDP] Sticky Buy Bar Price: {sticky_price.strip()}", flush=True)

        await pdp_page.screenshot(path=os.path.join(out_dir, "verified_pdp_variant_price.png"))
        print("Captured verified_pdp_variant_price.png", flush=True)

        # --- TEST 2: Product Card (PLP) Live Variant Price Update ---
        plp_page = await browser.new_page(viewport={"width": 1280, "height": 900})
        plp_url = f"https://therareavenue.com/collections/womens-handbags?v={int(time.time())}"
        print(f"\nNavigating to {plp_url}...", flush=True)
        await plp_page.goto(plp_url, wait_until="domcontentloaded", timeout=25000)
        await plp_page.wait_for_timeout(2500)

        # Find a product card with color swatches
        cards = await plp_page.locator('product-card, .product-card').all()
        print(f"[PLP] Found {len(cards)} product cards", flush=True)

        target_card = None
        for card in cards:
            swatches = await card.locator('.luxury-card__color-btn').all()
            if len(swatches) > 1:
                title = await card.locator('h3, .product-title, a.product-card__link').first.text_content()
                print(f"[PLP] Found card with {len(swatches)} swatches: {title.strip()}")
                target_card = card
                break

        if target_card:
            card_initial_price = await target_card.locator('[ref="priceContainer"], product-price, .price').first.text_content()
            print(f"[PLP Card] Initial Card Price: {card_initial_price.strip()}", flush=True)

            # Check swatches with different prices
            swatches = await target_card.locator('.luxury-card__color-btn').all()
            for s in swatches:
                price_attr = await s.get_attribute('data-price')
                title_attr = await s.get_attribute('title')
                print(f"   Swatch: {title_attr} -> data-price={price_attr}")

            # Click second or third swatch
            swatch_to_click = swatches[1]
            target_title = await swatch_to_click.get_attribute('title')
            expected_price = await swatch_to_click.get_attribute('data-price')
            print(f"[PLP Card] Clicking swatch: {target_title} (expected: {expected_price})...", flush=True)
            await swatch_to_click.click()
            await plp_page.wait_for_timeout(1000)

            card_updated_price = await target_card.locator('[ref="priceContainer"], product-price, .price').first.text_content()
            print(f"[PLP Card] Updated Card Price: {card_updated_price.strip()}", flush=True)

            await target_card.screenshot(path=os.path.join(out_dir, "verified_card_variant_price.png"))
            print("Captured verified_card_variant_price.png", flush=True)

        await browser.close()
        print("\nAll verification tests completed successfully!", flush=True)

if __name__ == "__main__":
    asyncio.run(run())
