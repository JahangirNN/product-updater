"""
Verify iPad Mini header layout across all viewports on live store https://therareavenue.com
"""
import asyncio
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\Jahangir\.gemini\antigravity\brain\5a5cc45f-5127-4b1a-a581-3e2bc159c5fb"

VIEWPORTS = [
    ("ipad_mini_portrait_768", 768, 1024, True, "iPad Mini Portrait (768px)"),
    ("ipad_mini_6_portrait_744", 744, 1133, True, "iPad Mini 6 Portrait (744px)"),
    ("ipad_mini_landscape_1024", 1024, 768, True, "iPad Mini Landscape (1024px)"),
    ("ipad_mini_6_landscape_1133", 1133, 744, True, "iPad Mini 6 Landscape (1133px)"),
    ("desktop_baseline_1280", 1280, 800, False, "Desktop Baseline (1280px)"),
]

async def verify_all():
    print("=" * 80)
    print("VERIFYING LIVE HEADER RESPONSIVENESS & IPAD MINI INTEGRITY")
    print("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        all_passed = True

        for key, w, h, is_touch, label in VIEWPORTS:
            print(f"\n--- Testing {label} ({w}x{h}, touch={is_touch}) ---")
            context = await browser.new_context(
                viewport={"width": w, "height": h},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1" if is_touch else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36",
                is_mobile=is_touch,
                has_touch=is_touch
            )
            page = await context.new_page()

            # Cache-bust with query param to ensure fresh assets
            await page.goto(f"https://therareavenue.com/?_v={os.urandom(4).hex()}", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Screenshot header
            header = page.locator("#header-component")
            shot_path = os.path.join(ARTIFACT_DIR, f"live_{key}.png")
            await header.screenshot(path=shot_path)
            print(f"Captured screenshot: {shot_path}")

            # Evaluate metrics and collisions
            data = await page.evaluate("""() => {
                const h = document.querySelector('#header-component');
                const menu = document.querySelector('header-menu');
                const drawer = document.querySelector('.header__drawer');
                const actions = document.querySelector('header-actions');
                const account = document.querySelector('.account-button');
                const cart = document.querySelector('.action__cart, button[data-testid="cart-drawer-trigger"]');
                const logo = document.querySelector('.header-logo');

                const csH = h ? window.getComputedStyle(h) : {};
                const csMenu = menu ? window.getComputedStyle(menu) : {};
                const csDrawer = drawer ? window.getComputedStyle(drawer) : {};

                const getR = el => {
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), right: Math.round(r.right) };
                };

                const menuRect = getR(menu);
                const actionsRect = getR(actions);
                const cartRect = getR(cart);
                const accountRect = getR(account);
                const drawerRect = getR(drawer);
                const logoRect = getR(logo);

                // Collision detection between menu and actions
                let collision = false;
                if (csMenu.display !== 'none' && menuRect && actionsRect && menuRect.w > 0 && actionsRect.w > 0) {
                    if (menuRect.right > actionsRect.x && menuRect.x < actionsRect.right) {
                        collision = true;
                    }
                }

                // Check both menu and drawer visible at same time
                const bothNavsVisible = csMenu.display !== 'none' && csDrawer.display !== 'none';

                const scrollWidth = document.documentElement.scrollWidth;
                const innerWidth = window.innerWidth;
                const overflow = scrollWidth > innerWidth;

                return {
                    menuStyle: h ? h.dataset.menuStyle : null,
                    menuDisplay: csMenu.display,
                    drawerDisplay: csDrawer.display,
                    menuRect,
                    actionsRect,
                    cartRect,
                    accountRect,
                    drawerRect,
                    logoRect,
                    collision,
                    bothNavsVisible,
                    overflow,
                    scrollWidth,
                    innerWidth
                };
            }""")

            print(f"  menuStyle: {data['menuStyle']}")
            print(f"  menuDisplay: {data['menuDisplay']}, drawerDisplay: {data['drawerDisplay']}")
            print(f"  drawerRect: {data['drawerRect']}")
            print(f"  logoRect: {data['logoRect']}")
            print(f"  menuRect: {data['menuRect']}")
            print(f"  actionsRect: {data['actionsRect']}")
            print(f"  cartRect: {data['cartRect']}")
            print(f"  collision: {data['collision']}")
            print(f"  bothNavsVisible: {data['bothNavsVisible']}")
            print(f"  overflow: {data['overflow']} (scrollWidth: {data['scrollWidth']}, innerWidth: {data['innerWidth']})")

            # Assertions
            passed = True
            if data["collision"]:
                print("  [FAIL]: Menu and Actions collide/overlap!")
                passed = False
            if data["bothNavsVisible"]:
                print("  [FAIL]: Both hamburger drawer and desktop menu are visible at the same time!")
                passed = False
            if data["overflow"]:
                print("  [FAIL]: Horizontal page overflow detected!")
                passed = False

            if passed:
                print("  [PASS]: Clean layout, 0 collisions, 0 overflow!")
            else:
                all_passed = False

            await context.close()

        await browser.close()

        print("\n" + "=" * 80)
        if all_passed:
            print("ALL VIEWPORTS PASSED VERIFICATION!")
        else:
            print("SOME VIEWPORTS FAILED!")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(verify_all())
