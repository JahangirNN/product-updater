"""
Verify mobile autoplay and absence of controls/resume icon on https://therareavenue.com/
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

URL = "https://therareavenue.com/"
OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\27dbd733-6117-47ed-838b-f053c708a71f"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # Emulate iPhone 14 Pro
    page = browser.new_page(
        viewport={"width": 390, "height": 844},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        is_mobile=True,
        has_touch=True
    )

    print(f"Loading {URL} on emulated iPhone 14 Pro...")
    page.goto(URL, wait_until="domcontentloaded")
    time.sleep(2)

    # Check DOM attributes immediately
    dom_state = page.evaluate("""() => {
        const vMedia = document.querySelector('.slideshow video-media.sm\\\\:hidden');
        const video = vMedia ? vMedia.querySelector('video') : null;
        if (!video) return { error: 'No mobile video found' };

        return {
            hasAutoplayAttr: video.hasAttribute('autoplay'),
            hasMutedAttr: video.hasAttribute('muted'),
            hasPlaysinlineAttr: video.hasAttribute('playsinline'),
            hasControlsAttr: video.hasAttribute('controls'),
            isControlsProperty: video.controls,
            isMutedProperty: video.muted,
            isPaused: video.paused,
            readyState: video.readyState,
            currentTime: video.currentTime,
            vMediaSuspended: vMedia.hasAttribute('suspended'),
            videoWidth: video.videoWidth,
            videoHeight: video.videoHeight,
            ratio: video.videoHeight ? (video.videoWidth / video.videoHeight).toFixed(3) : null
        };
    }""")
    print("\nInitial Mobile Video DOM State:")
    for k, v in dom_state.items():
        print(f"  {k}: {v}")

    # Wait 2 seconds and check playback progress
    time.sleep(2)
    progress_state = page.evaluate("""() => {
        const video = document.querySelector('.slideshow video-media.sm\\\\:hidden video');
        return {
            currentTime: video ? video.currentTime : 0,
            isPaused: video ? video.paused : true,
            hasControls: video ? video.hasAttribute('controls') : false
        };
    }""")
    print("\nAfter 2 seconds playback progress:")
    for k, v in progress_state.items():
        print(f"  {k}: {v}")

    shot_path = os.path.join(OUTPUT_DIR, "live_mobile_autoplay_verified.png")
    page.screenshot(path=shot_path)
    print(f"\nScreenshot saved to: {shot_path}")

    browser.close()
    print("Verification completed successfully!")
