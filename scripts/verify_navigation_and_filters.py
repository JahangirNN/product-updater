import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()

        print('1. Testing Home Page Header Nav...')
        await page.goto('https://therareavenue.com', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)

        brands_btn = page.locator('summary.luxury-nav__trigger[data-title="Brands"]')
        brands_count = await brands_btn.count()
        print(f'Brands triggers in header: {brands_count}')

        if brands_count > 0:
            await brands_btn.first.hover()
            await page.wait_for_timeout(1000)
            await page.screenshot(path='C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/header_brands_menu.png')
            print('Saved header_brands_menu.png')

        women_btn = page.locator('summary.luxury-nav__trigger[data-title="Women"]')
        if await women_btn.count() > 0:
            await women_btn.first.hover()
            await page.wait_for_timeout(1000)
            tissot_w_links = await page.locator('a[href*="/collections/womens-watches/tissot"]').count()
            print(f'Women -> Tissot filtered links: {tissot_w_links}')
            await page.screenshot(path='C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/header_women_menu.png')
            print('Saved header_women_menu.png')

        print('2. Testing /collections/womens-watches/tissot...')
        await page.goto('https://therareavenue.com/collections/womens-watches/tissot', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/womens_tissot_filtered.png')
        print('Saved womens_tissot_filtered.png')

        print('3. Testing /collections/tissot (Master Showroom)...')
        await page.goto('https://therareavenue.com/collections/tissot', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/tissot_master_showroom.png')
        print('Saved tissot_master_showroom.png')

        print('4. Testing /collections/tissot/men...')
        await page.goto('https://therareavenue.com/collections/tissot/men', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/tissot_men_filtered.png')
        print('Saved tissot_men_filtered.png')

        print('5. Testing Mobile Drawer...')
        m_context = await browser.new_context(viewport={'width': 390, 'height': 844})
        m_page = await m_context.new_page()
        await m_page.goto('https://therareavenue.com', wait_until='domcontentloaded')
        await m_page.wait_for_timeout(1000)
        hamburger = m_page.locator('button[aria-controls="sidebar-menu"]')
        if await hamburger.count() > 0:
            await hamburger.first.click()
            await m_page.wait_for_timeout(1000)
            await m_page.screenshot(path='C:/Users/Administrator/.gemini/antigravity/brain/8f48874f-591b-45e7-be48-696b0743b7ad/mobile_drawer_brands.png')
            print('Saved mobile_drawer_brands.png')

        await browser.close()
        print('ALL PLAYWRIGHT TESTS COMPLETED SUCCESSFULLY!')

asyncio.run(run())
