import os
import glob
import json

PROJECT_ROOT = "product-updater"
import sys
sys.path.insert(0, PROJECT_ROOT)

from storage.pricing_engine import load_pricing_rules, get_rule_for_product
from storage.shopify_taxonomy import resolve_product_type, resolve_authentic_vendor

rules = load_pricing_rules()
pattern = os.path.join(PROJECT_ROOT, "storage", "db", "**", "products", "*.json")
files = glob.glob(pattern, recursive=True)

unconfigured_by_store = {}
configured_by_store = {}

for f in files:
    try:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        store = (d.get("source_store") or d.get("store") or "unknown").lower()
        ptype = resolve_product_type(d)
        vendor = resolve_authentic_vendor(d)
        
        rule = get_rule_for_product(store, ptype, rules=rules, vendor=vendor)
        formula = rule.get("formula", "")
        
        if formula == "standard_forex" and rule.get("multiplier", 1.0) <= 1.0:
            if store not in unconfigured_by_store:
                unconfigured_by_store[store] = []
            unconfigured_by_store[store].append((ptype, vendor, d.get("title"), f))
        else:
            if store not in configured_by_store:
                configured_by_store[store] = []
            configured_by_store[store].append((ptype, vendor, d.get("title"), formula))
    except Exception as e:
        pass

print("=== STORES WITH PROFIT FORMULAS CONFIGURED ===")
for st, prods in configured_by_store.items():
    print(f"✅ {st.upper():15s}: {len(prods)} products (Formulas: {set(p[3] for p in prods)})")

print("\n=== STORES / PRODUCTS WITH ZERO PROFIT (FALLBACK TO STANDARD_FOREX MULTIPLIER 1.0) ===")
for st, prods in unconfigured_by_store.items():
    print(f"❌ {st.upper():15s}: {len(prods)} products have NO profit formula applied!")
    # show categories in this store
    cats = set(p[0] for p in prods)
    print(f"   Categories: {cats}")
