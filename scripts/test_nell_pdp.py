import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"

def test_nell():
    url = "https://therareavenue.com/products/nell-fringe-hardware-top-handle-bag-burgundy"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_msgs.append(f"[ERROR] {err}"))
        
        print(f"Opening {url}...")
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Take initial screenshot
        page.screenshot(path=os.path.join(ARTIFACTS_DIR, "nell_test_0_initial.png"))
        
        initial_img = page.evaluate("""() => {
            const gallery = document.querySelector('product-gallery');
            const visible = gallery ? Array.from(gallery.querySelectorAll('.product-gallery__media')).find(el => {
                const r = el.getBoundingClientRect();
                return r.top < window.innerHeight && r.bottom > 100;
            }) : null;
            return {
                imgSrc: visible && visible.querySelector('img') ? visible.querySelector('img').src : null,
                selectedVariant: document.querySelector('input[name=\"id\"]')?.value
            };
        }""")
        print("Initial state:", initial_img)
        
        # Click "Deep Brown"
        deep_brown_swatch = page.locator("label:has-text('Deep Brown'), [data-tooltip*='Deep Brown']").first
        if deep_brown_swatch.count() > 0:
            print("Clicking Deep Brown swatch...")
            deep_brown_swatch.click()
            page.wait_for_timeout(3000)
            page.screenshot(path=os.path.join(ARTIFACTS_DIR, "nell_test_1_deep_brown.png"))
            
            after_state = page.evaluate("""() => {
                const gallery = document.querySelector('product-gallery');
                const visible = gallery ? Array.from(gallery.querySelectorAll('.product-gallery__media')).find(el => {
                    const r = el.getBoundingClientRect();
                    return r.top < window.innerHeight && r.bottom > 100;
                }) : null;
                return {
                    imgSrc: visible && visible.querySelector('img') ? visible.querySelector('img').src : null,
                    selectedVariant: document.querySelector('input[name=\"id\"]')?.value,
                    scrollY: window.scrollY
                };
            }""")
            print("After Deep Brown click:", after_state)
            
            # Check if active image changed
            print("Did image change?", initial_img["imgSrc"] != after_state["imgSrc"])
            print("Did variant change?", initial_img["selectedVariant"] != after_state["selectedVariant"])
        else:
            print("Swatch Deep Brown NOT FOUND!")
            
        print("\nConsole errors / logs:")
        for m in console_msgs:
            if "error" in m.lower():
                print(" ", m)
                
        browser.close()

if __name__ == "__main__":
    test_nell()
