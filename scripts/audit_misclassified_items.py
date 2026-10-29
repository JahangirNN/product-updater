import os
import sys
import glob
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products
from storage.shopify_taxonomy import resolve_product_type, resolve_luxury_bag_silhouette

catalog = get_luxury_bag_products()

print("=" * 80)
print("AUDITING PRODUCT TYPES & SILHOUETTES ACROSS 1,199 ITEMS")
print("=" * 80)

for brand, prods in catalog.items():
    print(f"\n--- {brand.upper()} ({len(prods)} items) ---")
    shoe_like = []
    apparel_like = []
    silhouettes = {}
    
    for p in prods:
        title = p.get("title", "")
        pt = p.get("product_type", "")
        sil = resolve_luxury_bag_silhouette(p)
        resolved_pt = resolve_product_type(p)
        
        # Check for shoe terms
        shoe_terms = ["pump", "heel", "boot", "bootie", "loafer", "sandal", "sneaker", "flat", "mule", "shoe", "flex", "wedge", "espadrille", "clog"]
        if any(re.search(rf"\b{t}\b", title.lower()) for t in shoe_terms):
            shoe_like.append((p.get("id"), title, pt, sil, resolved_pt, [v.get("size") or v.get("title") for v in p.get("variants", [])[:3]]))
            
        silhouettes[sil] = silhouettes.get(sil, 0) + 1
        
    print(f"Silhouette breakdown: {silhouettes}")
    if shoe_like:
        print(f"WARNING: Found {len(shoe_like)} potential footwear items in {brand}:")
        for item in shoe_like:
            print(f"  ID: {item[0]} | Title: {item[1]} | Raw PT: {item[2]} | Sil: {item[3]} | Resolved: {item[4]} | Var: {item[5]}")
