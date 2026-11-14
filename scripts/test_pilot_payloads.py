import os
import sys
import json

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import prepare_product_set_payload

PILOT_FILES = {
    "Glossier": "00746b4ef0f45103.json",
    "MAKEUP BY MARIO": "0263b15b38529dfe.json",
    "Gisou": "026b5e220a9f4985.json",
    "REFY": "028a15e63b2cb6f9.json",
    "Haus Labs": "034159e1dcfe57b9.json",
    "Hourglass": "04c4dd45f575ba41.json",
    "PATRICK TA": "050a2d8ca25205a5.json",
    "Summer Fridays": "05266852db888a70.json",
    "Tower 28 Beauty": "05824dadb0d3488f.json",
    "MERIT": "064cffc5d3a5b0a4.json",
    "rhode": "0749eca097bf76c1.json",
    "Saie": "08702e1da9320ab5.json",
    "Kosas": "09fb3e7f2425a515.json",
    "Westman Atelier": "14f3a9acb4683314.json"
}

print(f"Testing payload generation for {len(PILOT_FILES)} pilot products:")
for brand, fn in PILOT_FILES.items():
    fp = os.path.join("product-updater", "storage", "db", "sephora", "products", fn)
    with open(fp, encoding="utf-8") as f:
        p = json.load(f)
    
    payload = prepare_product_set_payload(p, forex_rate=86.5)
    title = payload.get("title")
    vendor = payload.get("vendor")
    ptype = payload.get("productType")
    opts = [o["name"] for o in payload.get("productOptions", [])]
    var_cnt = len(payload.get("variants", []))
    tags = payload.get("tags", [])
    
    # Assertions
    assert vendor.lower() in brand.lower() or brand.lower() in vendor.lower(), f"Vendor mismatch: {vendor} vs {brand}"
    assert "Beauty" in tags or "Cosmetics" in tags or "Luxury Beauty" in tags, f"Missing Beauty tag for {title}"
    assert var_cnt > 0, f"0 variants for {title}"
    
    print(f"[{brand}] {title[:40]} | Vendor: {vendor} | Type: {ptype} | Options: {opts} | Variants: {var_cnt}")

print("\nALL 14 PILOT PAYLOADS VALIDATED 100% CLEAN!")
