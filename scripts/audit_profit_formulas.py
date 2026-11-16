import os
import glob
import json
from collections import defaultdict

PROJECT_ROOT = "product-updater"
import sys
sys.path.insert(0, PROJECT_ROOT)

from storage.pricing_engine import load_pricing_rules, get_rule_for_product
from storage.shopify_taxonomy import resolve_product_type, resolve_authentic_vendor

rules = load_pricing_rules()
pattern = os.path.join(PROJECT_ROOT, "storage", "db", "**", "products", "*.json")
files = glob.glob(pattern, recursive=True)

# Track:
# (store, category/ptype, vendor) -> count, rule_formula, rule_description
breakdown = defaultdict(lambda: {
    "count": 0,
    "formula": None,
    "description": None,
    "has_profit_markup": False,
    "sample_title": None,
    "sample_file": None
})

for f in files:
    try:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        
        store = (d.get("source_store") or d.get("store") or "unknown").lower()
        ptype = resolve_product_type(d)
        vendor = resolve_authentic_vendor(d)
        
        rule = get_rule_for_product(store, ptype, rules=rules, vendor=vendor)
        formula = rule.get("formula", "unknown")
        desc = rule.get("description", "")
        
        # Determine if profit markup is applied:
        # standard_forex with multiplier <= 1.0 is NO markup (0 profit!)
        # Any bracket or linear markup or multiplier > 1.0 is profit markup.
        has_markup = False
        if formula in ("linear_markup", "price_bracket_markup", "usd_tiered_percentage_markup", "discount_bracket_markup"):
            has_markup = True
        elif formula == "percentage_markup" and rule.get("multiplier", 1.0) > 1.0:
            has_markup = True
        elif formula == "standard_forex":
            has_markup = False
        
        key = (store, ptype)
        entry = breakdown[key]
        entry["count"] += 1
        entry["formula"] = formula
        entry["description"] = desc
        entry["has_profit_markup"] = has_markup
        if not entry["sample_title"]:
            entry["sample_title"] = d.get("title")
            entry["sample_file"] = f
            entry["vendor"] = vendor
    except Exception as e:
        pass

print("=" * 100)
print("CATALOG PROFIT FORMULA AUDIT")
print("=" * 100)

no_profit = []
with_profit = []

for (st, pt), data in sorted(breakdown.items(), key=lambda x: x[1]["count"], reverse=True):
    status_str = "✅ PROFIT MARKUP" if data["has_profit_markup"] else "❌ NO PROFIT FORMULA (COST ONLY / DEFAULT)"
    print(f"Store: {st:14s} | Category: {pt:25s} | Count: {data['count']:4d} | Formula: {data['formula']:28s} | {status_str}")
    if not data["has_profit_markup"]:
        no_profit.append(((st, pt), data))
    else:
        with_profit.append(((st, pt), data))

print("\n" + "=" * 100)
print(f"SUMMARY: {sum(d['count'] for _, d in with_profit)} products HAVE profit formula applied.")
print(f"SUMMARY: {sum(d['count'] for _, d in no_profit)} products HAVE NO profit formula applied (at risk / sold at cost price)!")
print("=" * 100)

print("\n--- CATEGORIES / STORES WITH NO PROFIT FORMULA ---")
for (st, pt), data in no_profit:
    print(f"• Store: {st.upper():12s} | Category: {pt:25s} | {data['count']} items | Vendor: {data.get('vendor')} | Sample: {data['sample_title'][:50]}")
