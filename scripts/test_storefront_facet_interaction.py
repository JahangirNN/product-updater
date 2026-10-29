import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        
        print("Navigating to https://therareavenue.com/collections/all ...")
        await page.goto("https://therareavenue.com/collections/all", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Let's inspect all forms, filter buttons, and checkboxes
        inputs = await page.locator("input[name^='filter']").all()
        print(f"Total filter inputs found: {len(inputs)}")
        for inp in inputs:
            name = await inp.get_attribute("name")
            val = await inp.get_attribute("value")
            id_ = await inp.get_attribute("id")
            print(f"  Input: name={name}, val={val}, id={id_}")

        # Check if there is a facets form
        form = page.locator("form[id*='facet'], form[class*='facet'], form[action*='collections']").first
        if await form.count() > 0:
            action = await form.get_attribute("action")
            id_ = await form.get_attribute("id")
            print(f"Facets form found: id={id_}, action={action}")

        # Let's try clicking a vendor checkbox, e.g., COACH or Citizen
        coach_cb = page.locator("input[value='COACH']").first
        if await coach_cb.count() > 0:
            print("Found COACH checkbox. Checking it...")
            await coach_cb.check(force=True)
            await page.wait_for_timeout(3000)
            print(f"URL after check: {page.url}")
            
            # Check what products appear
            product_cards = await page.locator(".product-card__title, .product-item__title, a.bold").all_inner_texts()
            print(f"Products after checking COACH ({len(product_cards)}):")
            for t in product_cards[:8]:
                print(f"  * {t}")
        else:
            print("COACH checkbox not found!")

        await browser.close()

asyncio.run(run())
