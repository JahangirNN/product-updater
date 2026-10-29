import asyncio
import json
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def diagnose_header():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        for width, height, name in [(768, 1024, "iPad Mini Portrait (768px)"), (1024, 768, "iPad Mini Landscape (1024px)")]:
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()
            await page.goto("https://therareavenue.com/")
            await page.wait_for_timeout(2500)

            # Analyze header layout
            analysis = await page.evaluate("""() => {
                const headerGroup = document.querySelector('#header-group') || document.querySelector('header');
                const header = document.querySelector('.header') || document.querySelector('header');
                const sections = document.querySelectorAll('#header-group > div, #header-group > section, .shopify-section-group-header-group');

                const logo = document.querySelector('.header__heading-logo, .header__heading, a[href=\"/\"] img, .header-logo');
                const nav = document.querySelector('header-menu, nav.header__inline-menu, .luxury-desktop-nav, nav');
                const icons = document.querySelector('.header__icons, .header-actions');
                const drawerToggle = document.querySelector('.header__icon--menu, .menu-drawer-container, summary[aria-label*=\"Menu\"]');

                function getBox(el) {
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return {
                        tag: el.tagName,
                        className: el.className,
                        display: s.display,
                        visibility: s.visibility,
                        opacity: s.opacity,
                        rect: { top: r.top, left: r.left, width: r.width, height: r.height, bottom: r.bottom, right: r.right },
                        innerHTML: el.innerHTML.slice(0, 200)
                    };
                }

                return {
                    sectionsCount: sections.length,
                    headerGroupRect: headerGroup ? headerGroup.getBoundingClientRect() : null,
                    headerRect: header ? header.getBoundingClientRect() : null,
                    headerClasses: header ? header.className : '',
                    logo: getBox(logo),
                    nav: getBox(nav),
                    icons: getBox(icons),
                    drawerToggle: getBox(drawerToggle),
                    allTopVisible: Array.from(document.querySelectorAll('#header-group *')).map(el => {
                        const r = el.getBoundingClientRect();
                        const s = window.getComputedStyle(el);
                        if (r.height > 10 && r.width > 10 && s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0') {
                            return {
                                tag: el.tagName,
                                className: String(el.className),
                                text: el.innerText ? el.innerText.trim().slice(0, 50) : '',
                                rect: { top: Math.round(r.top), left: Math.round(r.left), width: Math.round(r.width), height: Math.round(r.height), right: Math.round(r.right) }
                            };
                        }
                        return null;
                    }).filter(Boolean)
                };
            }""")

            print(f"=== ANALYSIS FOR {name} ===")
            print(f"Header Rect: {analysis.get('headerRect')}")
            print(f"Header Classes: {analysis.get('headerClasses')}")
            print(f"Logo: {analysis.get('logo')}")
            print(f"Nav: {analysis.get('nav')}")
            print(f"Icons: {analysis.get('icons')}")
            print(f"Drawer Toggle (Hamburger): {analysis.get('drawerToggle')}")
            print(f"Top Visible Elements in Header ({len(analysis.get('allTopVisible', []))} items):")
            for item in analysis.get('allTopVisible', [])[:20]:
                print(f"  {item['tag']} (.{item['className'][:30]}): rect={item['rect']} text='{item['text']}'")
            print("="*60)

            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(diagnose_header())
