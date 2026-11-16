import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto("https://therareavenue.com/products/teri-shoulder-bag", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3000)

        # Inspect the variant-picker HTML
        vp_html = await page.locator('variant-picker').first.inner_html()
        with open("teri_vp_dump.html", "w", encoding="utf-8") as f:
            f.write(vp_html)
        print("Wrote teri_vp_dump.html, length:", len(vp_html))

        # Check all inputs and labels
        inputs = await page.locator('variant-picker input').all()
        for inp in inputs[:8]:
            outer = await inp.evaluate("el => el.outerHTML")
            parent_outer = await inp.evaluate("el => el.parentElement.outerHTML")
            print("--- Input ---")
            print(outer)
            print("--- Parent ---")
            print(parent_outer[:200])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
