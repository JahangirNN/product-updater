#!/usr/bin/env python3
import json
import os
import sys
from camoufox.sync_api import Camoufox

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "storage", "sample_sephora_pdp.json")
url = "https://www.sephora.com/product/pocket-blush-P517483?skuId=2998102"
print(f"Connecting to Sephora: {url}")

with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=40000)
    
    prod_data = page.evaluate("""() => {
        const scripts = document.querySelectorAll('script');
        for (let s of scripts) {
            const txt = (s.textContent || '').trim();
            if (txt.startsWith('{"page":') && txt.includes('"product":')) {
                try {
                    const parsed = JSON.parse(txt);
                    return parsed.page ? parsed.page.product : null;
                } catch(e) {
                    return null;
                }
            }
        }
        return null;
    }""")

    if prod_data:
        print("Successfully extracted page.product JSON!")
        print("Keys:", list(prod_data.keys()))
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(prod_data, f, indent=2)
        print(f"Saved to {OUTPUT_PATH}")
    else:
        print("Failed to find page.product script.")
