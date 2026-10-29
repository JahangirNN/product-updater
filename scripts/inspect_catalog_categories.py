import os
import json
from collections import defaultdict, Counter

def analyze_catalog():
    db_root = "storage/db"
    stores = [d for d in os.listdir(db_root) if os.path.isdir(os.path.join(db_root, d)) and d not in ("history", "__pycache__")]

    stats = defaultdict(lambda: {"total": 0, "on_shopify": 0, "types": Counter(), "groups": Counter(), "genders": Counter()})
    
    # Global buckets
    macro_categories = Counter()
    macro_shopify = Counter()
    store_types = defaultdict(lambda: Counter())

    for store in stores:
        p_dir = os.path.join(db_root, store, "products")
        if not os.path.exists(p_dir):
            continue
        for fname in os.listdir(p_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(p_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    p = json.load(f)
                
                ptype = (p.get("product_type") or "").strip()
                groups = p.get("groups") or []
                gender = p.get("gender") or (p.get("specifications") or {}).get("Gender") or "Unspecified"
                is_shopify = bool(p.get("shopify_product_id"))
                
                stats[store]["total"] += 1
                if is_shopify:
                    stats[store]["on_shopify"] += 1
                stats[store]["types"][ptype] += 1
                for g in groups:
                    stats[store]["groups"][g] += 1
                stats[store]["genders"][gender] += 1
                
                # Deduce broad category:
                # 1. Watches
                # 2. Eyewear / Sunglasses
                # 3. Handbags / Bags / Wallets
                # 4. Shoes / Footwear / Sneakers
                # 5. Apparel / Clothing
                title_lower = (p.get("title") or "").lower()
                ptype_lower = ptype.lower()
                groups_lower = " ".join(groups).lower()
                combined = f"{title_lower} {ptype_lower} {groups_lower}"
                
                macro = "Other"
                if "watch" in combined or "timepiece" in combined or store == "jomashop":
                    macro = "Watches & Timepieces"
                elif "sunglass" in combined or "eyewear" in combined or "glasses" in combined:
                    macro = "Eyewear & Sunglasses"
                elif any(w in combined for w in ["bag", "tote", "crossbody", "satchel", "clutch", "backpack", "wallet", "wristlet", "handbag", "shoulder"]):
                    macro = "Luxury Bags & Leather Goods"
                elif any(w in combined for w in ["shoe", "sneaker", "boot", "sandal", "loafer", "heel", "footwear", "slide", "mule", "pump"]):
                    macro = "Footwear & Shoes"
                elif any(w in combined for w in ["dress", "jacket", "shirt", "pant", "hoodie", "top", "tee", "coat", "apparel"]):
                    macro = "Apparel & Ready-to-Wear"

                macro_categories[macro] += 1
                if is_shopify:
                    macro_shopify[macro] += 1
                store_types[store][macro] += 1

            except Exception:
                pass

    print("=== HIGH-LEVEL MACRO CATEGORY BREAKDOWN ===")
    for macro, cnt in macro_categories.most_common():
        shp = macro_shopify[macro]
        print(f"  * {macro:<32}: {cnt:4d} items total ({shp:4d} live on Shopify | {cnt - shp:4d} ready to onboard)")

    print("\n=== MACRO CATEGORIES BY STORE ===")
    for s, cat_cnts in sorted(store_types.items()):
        print(f"\n[{s.upper()}] (Total: {stats[s]['total']}, Live on Shopify: {stats[s]['on_shopify']})")
        for cat, c_num in cat_cnts.most_common():
            print(f"    - {cat:<30}: {c_num:3d} items")
        print(f"    Top specific types: {dict(stats[s]['types'].most_common(5))}")
        print(f"    Top groups:         {dict(stats[s]['groups'].most_common(5))}")

if __name__ == "__main__":
    analyze_catalog()
