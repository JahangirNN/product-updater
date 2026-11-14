import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto("https://therareavenue.com", wait_until="networkidle")
    time.sleep(2)
    
    info = page.evaluate("""() => {
        const el = document.querySelector('.header__icon--menu');
        if (!el) return 'Not found';
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const parentStyle = window.getComputedStyle(el.parentElement);
        return {
            rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
            display: style.display,
            visibility: style.visibility,
            opacity: style.opacity,
            parentDisplay: parentStyle.display
        };
    }""")
    print("Summary info:", info)
    
    # Try dispatching click event or calling open
    page.evaluate("""() => {
        const summary = document.querySelector('.header__icon--menu');
        if (summary) {
            summary.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        }
    }""")
    time.sleep(2)
    
    # check if drawer is now open
    drawerInfo = page.evaluate("""() => {
        const drawer = document.querySelector('header-drawer');
        const details = document.querySelector('#Details-menu-drawer-container');
        return {
            drawerClass: drawer ? drawer.className : 'no drawer',
            detailsOpen: details ? details.hasAttribute('open') : 'no details'
        };
    }""")
    print("Drawer info after click event:", drawerInfo)
    
    page.screenshot(path="C:/Users/Jahangir/.gemini/antigravity/brain/5a5cc45f-5127-4b1a-a581-3e2bc159c5fb/live_mobile_drawer_beauty.png")
    print("Screenshot saved to live_mobile_drawer_beauty.png")
    browser.close()
