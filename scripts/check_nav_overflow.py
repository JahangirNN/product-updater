import asyncio
import os
from playwright.async_api import async_playwright

STORE_URL = "https://therareavenue.com"

async def check_overflow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 800})
        await page.goto(STORE_URL, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)
        
        viewports = [1000, 1050, 1100, 1150, 1200, 1280, 1440]
        for w in viewports:
            await page.set_viewport_size({"width": w, "height": 800})
            await asyncio.sleep(0.5)
            
            nav_data = await page.evaluate('''() => {
                const nav = document.querySelector('.header__primary-nav');
                const triggers = Array.from(document.querySelectorAll('.header__primary-nav .luxury-nav__trigger'));
                const triggerData = triggers.map(t => {
                    const rect = t.getBoundingClientRect();
                    return { text: t.innerText.trim(), width: rect.width, left: rect.left, right: rect.right };
                });
                return {
                    clientWidth: nav.clientWidth,
                    scrollWidth: nav.scrollWidth,
                    offsetWidth: nav.offsetWidth,
                    triggers: triggerData
                };
            }''')
            
            scroll_overflow = nav_data['scrollWidth'] > nav_data['clientWidth']
            last_trigger = nav_data['triggers'][-1] if nav_data['triggers'] else None
            first_trigger = nav_data['triggers'][0] if nav_data['triggers'] else None
            total_triggers_width = last_trigger['right'] - first_trigger['left'] if last_trigger and first_trigger else 0
            
            print(f"Viewport {w}px: clientWidth={nav_data['clientWidth']:.1f}, scrollWidth={nav_data['scrollWidth']:.1f}, totalTriggersWidth={total_triggers_width:.1f}, Overflow={scroll_overflow}", flush=True)
            if scroll_overflow:
                print(f"  WARNING: Overflow detected at {w}px by {nav_data['scrollWidth'] - nav_data['clientWidth']:.1f}px!", flush=True)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_overflow())
