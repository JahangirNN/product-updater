import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def examine_ipad():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        for w, h, name in [(768, 1024, "iPad Mini Portrait 768px"), (1024, 768, "iPad Mini Landscape 1024px")]:
            context = await browser.new_context(
                viewport={"width": w, "height": h},
                user_agent="Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()
            await page.goto("https://therareavenue.com/")
            await page.wait_for_timeout(2500)

            # Let's inspect all elements visible in the top 120px
            elements = await page.evaluate("""() => {
                const results = [];
                const all = document.querySelectorAll('body *');
                for (const el of all) {
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    if (r.top < 120 && r.bottom > 0 && r.width > 5 && r.height > 5 && s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity) > 0) {
                        // Check if it's a leaf or has text/svg
                        const isLeaf = el.children.length === 0 || el.tagName === 'SVG' || el.tagName === 'BUTTON' || el.tagName === 'A' || el.tagName === 'SPAN';
                        if (isLeaf && (el.innerText || el.tagName === 'SVG' || el.tagName === 'IMG' || el.tagName === 'INPUT')) {
                            results.push({
                                tag: el.tagName,
                                id: el.id,
                                className: String(el.className || '').slice(0, 40),
                                text: (el.innerText || '').trim().slice(0, 30),
                                x: Math.round(r.x),
                                y: Math.round(r.y),
                                w: Math.round(r.width),
                                h: Math.round(r.height),
                                right: Math.round(r.right),
                                bottom: Math.round(r.bottom)
                            });
                        }
                    }
                }
                return results;
            }""")

            print(f"=== VISIBLE ELEMENTS IN TOP 120px FOR {name} ===")
            for el in elements:
                print(f"  [{el['tag']}] x={el['x']} y={el['y']} w={el['w']} h={el['h']} (right={el['right']}) text='{el['text']}' class='{el['className']}' id='{el['id']}'")
            print("="*60)
            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(examine_ipad())
