"""
Verify live responsive hero video behavior on desktop (16:9) and mobile (9:16) on https://therareavenue.com/
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

URL = "https://therareavenue.com/"
OUTPUT_DIR = r"C:\Users\Administrator\.gemini\antigravity\brain\27dbd733-6117-47ed-838b-f053c708a71f"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # 1. Desktop Verification (1440 x 900)
    print("--- TESTING DESKTOP VIEWPORT (1440 x 900) ---")
    page_desk = browser.new_page(viewport={"width": 1440, "height": 900})
    page_desk.goto(URL, wait_until="domcontentloaded")
    time.sleep(3)

    desk_data = page_desk.evaluate("""() => {
        const videos = Array.from(document.querySelectorAll('.slideshow video'));
        const vMedia = Array.from(document.querySelectorAll('.slideshow video-media'));
        return {
            totalVideos: videos.length,
            videoDetails: videos.map(v => {
                const rect = v.getBoundingClientRect();
                const style = window.getComputedStyle(v.closest('video-media') || v);
                return {
                    src: v.currentSrc || v.src,
                    display: style.display,
                    visible: rect.width > 0 && rect.height > 0 && style.display !== 'none',
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    videoWidth: v.videoWidth,
                    videoHeight: v.videoHeight,
                    ratio: v.videoHeight ? (v.videoWidth / v.videoHeight).toFixed(3) : null
                };
            })
        };
    }""")
    print("Desktop video details:")
    for v in desk_data["videoDetails"]:
        print(" ", v)

    desk_shot = os.path.join(OUTPUT_DIR, "hero_video_desktop_16_9.png")
    page_desk.screenshot(path=desk_shot)
    print(f"Desktop screenshot saved to: {desk_shot}")

    # 2. Mobile Verification (390 x 844)
    print("\n--- TESTING MOBILE VIEWPORT (390 x 844) ---")
    page_mob = browser.new_page(viewport={"width": 390, "height": 844})
    page_mob.goto(URL, wait_until="domcontentloaded")
    time.sleep(3)

    mob_data = page_mob.evaluate("""() => {
        const videos = Array.from(document.querySelectorAll('.slideshow video'));
        return {
            totalVideos: videos.length,
            videoDetails: videos.map(v => {
                const rect = v.getBoundingClientRect();
                const style = window.getComputedStyle(v.closest('video-media') || v);
                return {
                    src: v.currentSrc || v.src,
                    display: style.display,
                    visible: rect.width > 0 && rect.height > 0 && style.display !== 'none',
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    videoWidth: v.videoWidth,
                    videoHeight: v.videoHeight,
                    ratio: v.videoHeight ? (v.videoWidth / v.videoHeight).toFixed(3) : null
                };
            })
        };
    }""")
    print("Mobile video details:")
    for v in mob_data["videoDetails"]:
        print(" ", v)

    mob_shot = os.path.join(OUTPUT_DIR, "hero_video_mobile_9_16.png")
    page_mob.screenshot(path=mob_shot)
    print(f"Mobile screenshot saved to: {mob_shot}")

    browser.close()
    print("\nVerification completed successfully!")
