import asyncio
from playwright.async_api import async_playwright

PARTNER_STORES = {
    "Coach": "pouch-in-signature-canvas",
    "Jomashop": "tissot-carson-watch-t1224071105100",
    "Michael Kors": "cherie-leather-sandal",
    "JW PEI": "hana-large-tote-bag-pink",
    "Nordstrom": "w-clifton-11-gtx-glm",
    "JD Sports": "womens-nike-dunk-low-patent-leather-casual-shoes-pink-foam-black-white-3337873",
    "Foot Locker": "adidas-originals-handball-spezial-loafers-women-s-maroon-maroon-kk2780"
}

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        for store, handle in PARTNER_STORES.items():
            url = f"https://therareavenue.com/products/{handle}"
            res = await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(1000)
            
            chk = page.locator("#checkcheck-addon-checkbox")
            count = await chk.count()
            print(f"[{store}] handle={handle} -> HTTP {res.status if res else None}, Checkbox Count: {count}")
            if count == 0:
                print(f"  Page title: {await page.title()}")
                # Check what buttons or forms exist
                forms = await page.locator("form[action*='/cart/add']").count()
                buy_btns = await page.locator("buy-buttons").count()
                print(f"  Forms: {forms}, buy-buttons custom element: {buy_btns}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
