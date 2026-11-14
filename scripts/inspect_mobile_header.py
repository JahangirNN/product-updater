import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto("https://therareavenue.com", wait_until="networkidle")
    time.sleep(2)
    
    html = page.evaluate("""() => {
        const header = document.querySelector('header, .header');
        return header ? header.innerHTML : 'No header';
    }""")
    print("Header HTML snippet:")
    for line in html.split('\n')[:40]:
        print(line[:120])
    
    # check how drawer is opened
    triggers = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('button, summary, a')).map(el => ({
            tag: el.tagName,
            cls: el.className,
            id: el.id,
            aria: el.getAttribute('aria-label') || el.getAttribute('aria-controls'),
            text: el.innerText ? el.innerText.trim() : ''
        })).filter(x => x.aria || x.cls.includes('menu') || x.cls.includes('drawer'));
    }""")
    print("\nRelevant triggers:")
    for t in triggers[:15]:
        print(t)
    browser.close()
