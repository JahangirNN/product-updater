import os
import asyncio
from playwright.async_api import async_playwright

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 600px;
    height: 600px;
    background: #0f1211;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }
  .cert-card {
    width: 520px;
    height: 520px;
    background: radial-gradient(circle at 50% 30%, #1a2420 0%, #0d1210 100%);
    border: 2px solid #c9a876;
    border-radius: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 32px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.6), inset 0 0 30px rgba(201,168,118,0.15);
    position: relative;
    overflow: hidden;
  }
  .inner-border {
    position: absolute;
    top: 12px;
    left: 12px;
    right: 12px;
    bottom: 12px;
    border: 1px dashed rgba(201,168,118,0.4);
    border-radius: 16px;
    pointer-events: none;
  }
  .shield-icon {
    width: 90px;
    height: 90px;
    margin-bottom: 16px;
    filter: drop-shadow(0 4px 12px rgba(16,185,129,0.4));
  }
  .motto {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    color: #c9a876;
    text-transform: uppercase;
    margin-bottom: 8px;
  }
  .main-title {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    line-height: 1.25;
    margin-bottom: 6px;
  }
  .subtitle {
    font-size: 14px;
    font-weight: 600;
    color: #10b981;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 20px;
  }
  .divider {
    width: 80px;
    height: 2px;
    background: linear-gradient(90deg, transparent, #c9a876, transparent);
    margin-bottom: 18px;
  }
  .badge-tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(16,185,129,0.15);
    border: 1px solid rgba(16,185,129,0.4);
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    color: #34d399;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .footer-text {
    margin-top: 16px;
    font-size: 10px;
    letter-spacing: 1px;
    color: #88998e;
    text-transform: uppercase;
  }
</style>
</head>
<body>
<div class="cert-card">
  <div class="inner-border"></div>
  <svg class="shield-icon" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M50 8L15 24V50C15 72 30 90 50 96C70 90 85 72 85 50V24L50 8Z" fill="#10B981" fill-opacity="0.2" stroke="#10B981" stroke-width="4" stroke-linejoin="round"/>
    <path d="M50 16L22 29V50C22 68 34 83 50 88C66 83 78 68 78 50V29L50 16Z" fill="#064E3B" stroke="#34D399" stroke-width="2"/>
    <path d="M35 50L45 60L65 40" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
  <div class="motto">Official 3rd-Party Verification</div>
  <div class="main-title">Certificate of<br>Authenticity</div>
  <div class="subtitle">CheckCheck &times; The Rare Avenue</div>
  <div class="divider"></div>
  <div class="badge-tag">
    <span>●</span> Serialized Green Tag &amp; Digital COA
  </div>
  <div class="footer-text">Dual-Expert 4-Hour Sourced Evaluation</div>
</div>
</body>
</html>
"""

async def generate():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 600, "height": 600})
        await page.set_content(HTML_CONTENT)
        out_path = r"product-updater\horizon_clean_theme\assets\checkcheck-square-seal.png"
        await page.screenshot(path=out_path)
        await browser.close()
        print("Generated:", out_path, os.path.exists(out_path), os.path.getsize(out_path))

if __name__ == "__main__":
    asyncio.run(generate())
