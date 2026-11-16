import os
import glob
import json

PROJECT_ROOT = "product-updater"
import sys
sys.path.insert(0, PROJECT_ROOT)

from storage.pricing_engine import resolve_storefront_pricing
from storage.shopify_taxonomy import resolve_product_type, resolve_authentic_vendor
from storage.forex import get_usd_to_inr_rate

files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "nordstrom", "products", "*.json"))
print(f"Total Nordstrom products in DB: {len(files)}")

fx = get_usd_to_inr_rate()
print(f"Forex rate: {fx}")

shoes = []
for f in files:
    with open(f, "r", encoding="utf-8") as fp:
        d = json.load(fp)
    vendor = resolve_authentic_vendor(d)
    ptype = resolve_product_type(d)
    if vendor in ("On", "HOKA", "Salomon") or "shoe" in ptype.lower() or "sneaker" in ptype.lower():
        usd = float(d.get("source_price") or d.get("price_current") or 0.0)
        comp_usd = float(d.get("source_compare_at_price") or 0.0)
        inr_price, inr_comp = resolve_storefront_pricing(usd, comp_usd, "nordstrom", ptype, fx, vendor=vendor)
        base_cost = usd * fx
        effective_markup = ((inr_price / base_cost) - 1.0) * 100 if base_cost > 0 else 0
        shoes.append({
            "title": d.get("title"),
            "vendor": vendor,
            "ptype": ptype,
            "usd": usd,
            "base_cost_inr": round(base_cost, 2),
            "inr_price": inr_price,
            "effective_markup_pct": round(effective_markup, 1),
            "shopify_id": d.get("shopify_product_id")
        })

print(f"Total Nordstrom shoes: {len(shoes)}")
print("\nSample Nordstrom Shoes Pricing:")
for s in shoes[:10]:
    print(f"[{s['vendor']}] {s['title'][:40]:40s} | USD: ${s['usd']:6.2f} | Base INR: ₹{s['base_cost_inr']:8.2f} | Storefront INR: ₹{s['inr_price']:8.2f} | Markup: {s['effective_markup_pct']}%")
