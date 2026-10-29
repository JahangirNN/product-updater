"""
Verify live marquee performance, 60fps compositor animation, hover-pause, and thumbnail interactivity on https://therareavenue.com/
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

URL = "https://therareavenue.com/"
SCREENSHOT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\27dbd733-6117-47ed-838b-f053c708a71f"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    print(f"Navigating to {URL}...")
    page.goto(URL, wait_until="domcontentloaded")
    time.sleep(3)

    # Find the Curated Portfolios section
    elem = page.query_selector(".marquee-collection-section")
    if not elem:
        print("ERROR: .marquee-collection-section not found on page!")
        browser.close()
        sys.exit(1)

    elem.scroll_into_view_if_needed()
    time.sleep(1.5)

    print("\n--- MEASURING 60-FRAME LIVE ANIMATION PERFORMANCE ---")
    perf_data = page.evaluate("""() => {
        return new Promise((resolve) => {
            const rail = document.querySelector('marquee-collection-rail');
            const track = document.querySelector('.marquee-rail__track');
            const groupA = document.querySelector('.marquee-rail__group[data-group="a"]');

            const style = window.getComputedStyle(track);
            const animName = style.animationName;
            const animPlayState = style.animationPlayState;
            const animDuration = style.animationDuration;

            const frameDeltas = [];
            let lastTime = performance.now();
            let frames = 0;

            function recordFrame(now) {
                const delta = now - lastTime;
                lastTime = now;
                frameDeltas.push(delta);
                frames++;
                if (frames < 90) {
                    requestAnimationFrame(recordFrame);
                } else {
                    const cleanDeltas = frameDeltas.slice(5); // skip initial warmup
                    const avg = cleanDeltas.reduce((a, b) => a + b, 0) / cleanDeltas.length;
                    const max = Math.max(...cleanDeltas);
                    const min = Math.min(...cleanDeltas);
                    const fps = 1000 / avg;

                    resolve({
                        animName,
                        animPlayState,
                        animDuration,
                        cardCount: groupA ? groupA.querySelectorAll('.marquee-card').length : 0,
                        avgFrameDeltaMs: avg.toFixed(2),
                        effectiveFps: fps.toFixed(1),
                        maxFrameDeltaMs: max.toFixed(2),
                        minFrameDeltaMs: min.toFixed(2),
                        isClean60Fps: max < 28.0 && avg < 18.0
                    });
                }
            }
            requestAnimationFrame(recordFrame);
        });
    }""")

    for k, v in perf_data.items():
        print(f"  {k}: {v}")

    print("\n--- TESTING HOVER-PAUSE BEHAVIOR ---")
    # Hover over the rail
    rail = page.query_selector(".marquee-rail")
    rail.hover()
    time.sleep(0.5)

    hover_state = page.evaluate("""() => {
        const track = document.querySelector('.marquee-rail__track');
        return window.getComputedStyle(track).animationPlayState;
    }""")
    print(f"  Hover animation-play-state: {hover_state} (Expected: paused)")

    # Move mouse away
    page.mouse.move(10, 10)
    time.sleep(0.5)

    unhover_state = page.evaluate("""() => {
        const track = document.querySelector('.marquee-rail__track');
        return window.getComputedStyle(track).animationPlayState;
    }""")
    print(f"  Unhover animation-play-state: {unhover_state} (Expected: running)")

    print("\n--- TESTING 4-PIECE THUMBNAIL SWITCHING ---")
    thumb_test = page.evaluate("""() => {
        const firstCard = document.querySelector('.marquee-card');
        if (!firstCard) return { error: 'No card found' };

        const thumbs = firstCard.querySelectorAll('.marquee-card__thumb');
        const stageImages = firstCard.querySelectorAll('.marquee-card__image');

        if (thumbs.length < 2) return { error: 'Not enough thumbs' };

        // Click 2nd thumb
        thumbs[1].click();
        const activeThumbIdx = thumbs[1].classList.contains('is-active') ? 1 : -1;
        const activeStageIdx = stageImages[1].classList.contains('is-active') ? 1 : -1;

        return {
            totalThumbs: thumbs.length,
            totalStages: stageImages.length,
            thumb1ActiveAfterClick: activeThumbIdx === 1,
            stage1ActiveAfterClick: activeStageIdx === 1
        };
    }""")
    print(f"  Thumbnail switching result: {thumb_test}")

    # Take screenshot of the live section
    screenshot_path = os.path.join(SCREENSHOT_DIR, "live_curated_portfolios_marquee.png")
    elem.screenshot(path=screenshot_path)
    print(f"\nScreenshot saved to: {screenshot_path}")

    browser.close()
    print("Verification completed successfully!")
