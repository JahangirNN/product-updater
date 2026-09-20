"""
Catalog Data Exporter for Frontend Viewer
Reads partitioned local JSON database and compiles static JSON bundles for GitHub Pages.
Pure functions, zero classes (ADR 0004, ADR 0005).
"""
import os
import sys
import json
import time
from typing import Dict, Any, List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def classify_subgroup(product: Dict[str, Any]) -> str:
    """
    Classify product into Level 3 Subgroup based on title and specifications.
    Supports JW PEI, Nordstrom On, Michael Kors, and Coach.
    """
    title_lower = product.get("title", "").lower()
    handle_lower = product.get("handle", "").lower()
    specs = product.get("specifications", {})
    source_store = product.get("source_store", "").lower()
    groups = [g.lower() for g in product.get("groups", [])]
    text = f"{title_lower} {handle_lower}"

    # Coach multi-category taxonomy
    if source_store == "coach":
        pt = product.get("product_type", "")
        gender = product.get("gender", "Women")

        # Footwear
        if pt == "Shoes & Footwear":
            if any(w in text for w in ["sneaker", "runner", "trainer"]):
                return "Sneakers & Trainers"
            elif any(w in text for w in ["sandal", "slide", "flip flop", "espadrille"]):
                return "Sandals & Slides"
            elif any(w in text for w in ["boot", "bootie", "chukka"]):
                return "Boots & Booties"
            elif any(w in text for w in ["heel", "pump", "slingback", "wedge"]):
                return "Heels & Pumps"
            elif any(w in text for w in ["loafer", "mule", "mary jane", "ballet", "flat", "clog", "derby", "driver", "slipper"]):
                return "Loafers, Drivers & Flats"
            return "Designer Footwear"

        # Wallets & Small Goods
        if pt in ("Wallets & Small Goods", "Wristlets"):
            if "wristlet" in text:
                return "Wristlets"
            elif any(w in text for w in ["card case", "cardholder", "card id", "id case", "id card", "id wallet", "id lanyard", "key case", "lanyard", "holder wallet"]):
                return "Card Cases & ID Holders"
            elif any(w in text for w in ["3-in-1", "billfold", "bifold"]):
                return "Billfolds & Passcases"
            elif any(w in text for w in ["corner zip", "double zip", "zip around", "zip-around", "continental", "long wallet", "accordion"]):
                return "Zip & Continental Wallets"
            elif any(w in text for w in ["snap", "tri-fold", "trifold", "medium wallet", "small wallet", "compact", "flap"]):
                return "Compact & Trifold Wallets"
            if not any(w in text for w in ["bag", "plaza", "crossbody", "shoulder"]):
                return "Wallets & Small Leather Goods"

        # Backpacks
        if pt == "Backpacks" or "backpack" in text:
            return "Backpacks"

        # Men's Work & Messenger Bags
        if any(w in text for w in ["brief", "workbag", "portfolio", "messenger", "flight bag"]):
            return "Briefcases & Messengers"

        # Belt / Sling Bags
        if any(w in text for w in ["sling", "pack", "belt bag"]):
            return "Belt & Sling Bags"

        # Totes & Carryalls
        if any(w in text for w in ["tote", "carryall", "shopper", "cabu"]):
            return "Totes & Carryalls"

        # Satchels & Top Handles / Barrel / Bucket / Frame
        if any(w in text for w in ["satchel", "top handle", "top-handle", "barrel", "rowan", "bucket", "drawstring", "kisslock"]):
            return "Satchels & Top Handles"

        # Crossbody & Pouches
        if any(w in text for w in ["crossbody", "camera bag"]):
            return "Crossbody Bags"
        if any(w in text for w in ["nolita", "pouch", "clutch"]):
            return "Pouches & Clutches"

        # Shoulder Bags
        if any(w in text for w in ["shoulder", "hobo", "swinger", "teri", "plaza", "payton"]):
            return "Shoulder Bags"

        # Duffle & Travel
        if any(w in text for w in ["duffle", "travel"]):
            return "Duffles & Travel Bags"

        return "Designer Handbags"

    # Michael Kors multi-category taxonomy with strict Men & Women separation
    if source_store == "michaelkors":
        gender = product.get("gender", "Women")
        cat = product.get("product_type", "Handbags")
        text = f"{title_lower} {handle_lower}"
        
        if gender == "Men":
            if cat == "Shoes":
                if any(w in text for w in ["trainer", "sneaker"]):
                    return "Lace-Up Trainers"
                elif any(w in text for w in ["loafer", "moccasin"]):
                    return "Loafers & Moccasins"
                elif any(w in text for w in ["boot", "bootie"]):
                    return "Boots & Booties"
                elif any(w in text for w in ["slide", "sandal", "boat"]):
                    return "Slides & Casual"
                return "Designer Footwear"
            elif cat == "Belts":
                if any(w in text for w in ["reversible"]):
                    return "Reversible Belts"
                elif any(w in text for w in ["braided", "woven"]):
                    return "Braided Belts"
                return "Leather Belts"
            elif cat == "Wallets":
                if any(w in text for w in ["card"]):
                    return "Card Cases & Holders"
                elif any(w in text for w in ["billfold"]):
                    return "Billfolds"
                return "Wallets & Folios"
            return "Men's Luxury"

        # Women's Collections
        if cat == "Handbags":
            if any(w in text for w in ["tote", "shopper"]):
                return "Tote Bags"
            elif any(w in text for w in ["crossbody", "camera bag", "messenger"]):
                return "Crossbody Bags"
            elif any(w in text for w in ["shoulder", "pochette", "hobo"]):
                return "Shoulder Bags"
            elif any(w in text for w in ["satchel", "top handle", "top-handle"]):
                return "Satchels & Top Handles"
            elif any(w in text for w in ["clutch", "wristlet", "evening"]):
                return "Clutches & Evening"
            elif any(w in text for w in ["backpack"]):
                return "Backpacks"
            return "Shoulder Bags"
        elif cat == "Wallets":
            if any(w in text for w in ["card case", "cardholder", "card"]):
                return "Card Cases & Holders"
            elif any(w in text for w in ["wristlet"]):
                return "Wristlets"
            elif any(w in text for w in ["billfold"]):
                return "Billfolds"
            elif any(w in text for w in ["continental", "flap", "zip around", "zip-around", "large"]):
                return "Continental & Flap Wallets"
            return "Compact Wallets"
        elif cat == "Sneakers":
            if any(w in text for w in ["platform"]):
                return "Platform Sneakers"
            elif any(w in text for w in ["slip-on", "slip on"]):
                return "Slip-On Sneakers"
            elif any(w in text for w in ["trainer", "lace-up", "lace up"]):
                return "Lace-Up Trainers"
            return "Fashion Sneakers"
        elif cat == "Sandals":
            if any(w in text for w in ["wedge", "espadrille"]):
                return "Wedge & Espadrille Sandals"
            elif any(w in text for w in ["slide", "mule"]):
                return "Slides & Mules"
            elif any(w in text for w in ["gladiator", "strappy"]):
                return "Strappy & Gladiator"
            elif any(w in text for w in ["platform"]):
                return "Platform Sandals"
            return "Heeled & Flat Sandals"
        elif cat == "Flats":
            if any(w in text for w in ["mule"]):
                return "Mules & Clogs"
            elif any(w in text for w in ["loafer"]):
                return "Loafers"
            elif any(w in text for w in ["moccasin"]):
                return "Moccasins"
            elif any(w in text for w in ["ballet"]):
                return "Ballet Flats"
            elif any(w in text for w in ["espadrille"]):
                return "Espadrilles"
            return "Loafers & Flats"
        elif cat == "Boots":
            if any(w in text for w in ["knee-high", "knee high"]):
                return "Knee-High Boots"
            return "Ankle Boots & Booties"
        elif cat == "Sunglasses":
            if any(w in text for w in ["blue light", "optical"]):
                return "Blue Light Eyewear"
            color = specs.get("Color", "").lower()
            if any(c in color for c in ["gold", "silver", "rose gold", "metal"]):
                return "Metal Frame Sunglasses"
            elif any(c in color for c in ["tortoise", "horn", "black", "tort", "blush horn", "dark tortoise"]):
                return "Acetate Frame Sunglasses"
            return "Designer Sunglasses"
        return "Women's Luxury"

    # Footwear taxonomy for Nordstrom (On, HOKA, Salomon)
    if source_store == "nordstrom":
        if "waterproof" in title_lower or "waterproof" in handle_lower or "gtx" in title_lower or "gore-tex" in title_lower:
            return "Waterproof Footwear"
        elif "trail" in title_lower or "hiking" in title_lower or "hike" in handle_lower or "speedcross" in title_lower:
            return "Trail & Outdoor"
        elif "roger" in title_lower or "tennis" in title_lower or "court" in title_lower:
            return "Tennis & Court"
        elif "training" in title_lower or "pulse" in title_lower or "cloud x" in title_lower:
            return "Training & Gym"
        elif "mule" in title_lower or "slide" in title_lower or "clog" in title_lower or "slip on" in title_lower or "slip-on" in title_lower or "moc" in title_lower:
            return "Mules & Slides"
        elif "surfer" in title_lower or "runner" in title_lower or "monster" in title_lower or "running" in title_lower or "boom" in title_lower:
            return "Running Shoes"
        elif "coast" in title_lower or "nova" in title_lower or "tilt" in title_lower or "sneaker" in title_lower:
            return "Lifestyle & Casual"
        return "Performance Footwear"

    # Foot Locker Nike Vomero styles
    if source_store == "footlocker":
        if "roam" in text:
            return "Vomero Roam"
        elif "plus" in text:
            return "Vomero Plus"
        elif "18" in text:
            return "Vomero 18"
        elif "17" in text:
            return "Vomero 17"
        elif "5" in text or "zoom" in text:
            return "Vomero 5"
        return "Vomero Series"

    # JD Sports Nike Footwear Collections
    if source_store == "jdsports":
        sizing_cat = product.get("sizing_category", "Adult")
        if sizing_cat == "Toddler":
            return "Toddler & Infant"
        elif sizing_cat == "Preschool":
            return "Little Kids (Preschool)"
        elif sizing_cat == "Grade School":
            return "Big Kids (Grade School)"

        t_check = f"{title_lower} {handle_lower}"
        if "air max" in t_check or "vapormax" in t_check:
            if "90" in t_check:
                return "Air Max 90"
            elif "95" in t_check:
                return "Air Max 95"
            elif "97" in t_check:
                return "Air Max 97"
            elif "270" in t_check:
                return "Air Max 270"
            elif "plus" in t_check:
                return "Air Max Plus"
            elif "vapormax" in t_check:
                return "Air VaporMax"
            return "Air Max Classics"
        elif "air force" in t_check:
            return "Air Force 1"
        elif "dunk" in t_check:
            return "Dunk Low"
        return "Nike Footwear"

    # Handbags taxonomy for JW PEI
    style = specs.get("Carrying Style", "").lower() or specs.get("Carrying Method", "").lower()

    if "wallet" in title_lower or "wallet" in handle_lower or "card" in title_lower:
        return "Wallets & Small Goods"
    elif "tote" in title_lower or "tote" in handle_lower:
        return "Tote Bags"
    elif "mini" in title_lower or "mini" in handle_lower:
        return "Mini Bags"
    elif "woven" in title_lower or "weave" in title_lower or "rattan" in title_lower:
        return "Woven & Textured"
    elif "crossbody" in title_lower or "crossbody" in handle_lower or "crossbody" in style:
        return "Crossbody Bags"
    elif "shoulder" in title_lower or "shoulder" in handle_lower or "shoulder" in style:
        return "Shoulder Bags"
    elif "vanity" in title_lower or "box" in title_lower or "clutch" in title_lower:
        return "Vanity & Clutches"
    elif "top handle" in title_lower or "top-handle" in handle_lower:
        return "Top Handle Bags"
    return "Classic Handbags"


def format_viewer_product(
    prod: Dict[str, Any],
    store_display: str,
    group_display: str,
    subgroup_display: str,
    canonical_variant_map: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Format and streamline product record for high-speed frontend catalog viewer consumption."""
    variants = []
    for v in prod.get("variants", []):
        if not isinstance(v, dict):
            continue
        v_sku = v.get("sku", "")
        in_stock_val = bool(v.get("in_stock", False) or v.get("is_available", False))
        price_val = str(v.get("price", ""))
        source_price_val = float(v.get("source_price") or 0.0)

        # Cross-sibling canonical reconciliation:
        # If this variant corresponds to a sibling product in the catalog, always
        # reflect the sibling's exact, live stock and price state.
        if canonical_variant_map and v_sku in canonical_variant_map:
            canon = canonical_variant_map[v_sku]
            in_stock_val = canon["in_stock"]
            if canon.get("price"):
                price_val = canon["price"]
            if canon.get("source_price"):
                source_price_val = canon["source_price"]

        v_entry = {
            "sku": v_sku,
            "title": v.get("title", ""),
            "price": price_val,
            "source_price": source_price_val,
            "in_stock": in_stock_val,
        }
        if v.get("image_url"):
            v_entry["image_url"] = v["image_url"]
        if v.get("option_values"):
            v_entry["option_values"] = v["option_values"]
        variants.append(v_entry)

    raw_desc = prod.get("descriptionHtml") or prod.get("description_html") or ""
    desc_html = raw_desc.strip()

    images = prod.get("images", [])
    if isinstance(images, list):
        images = images[:5]
    else:
        images = []

    prod_title = prod.get("title", "")
    if prod.get("source_store") in ("footlocker", "jdsports"):
        color = (prod.get("specifications") or {}).get("Color")
        if color and color.lower() not in prod_title.lower():
            prod_title = f"{prod_title} - {color}"

    return {
        "id": str(prod.get("id") or prod.get("product_id") or ""),
        "source_store": prod.get("source_store", ""),
        "source_url": prod.get("source_url", ""),
        "handle": prod.get("handle", ""),
        "title": prod_title,
        "vendor": prod.get("vendor", ""),
        "product_type": prod.get("product_type", ""),
        "source_sku": prod.get("source_sku") or prod.get("sku") or "",
        "source_price": float(prod.get("source_price") or 0.0),
        "source_compare_at_price": prod.get("source_compare_at_price"),
        "price_range_usd": prod.get("price_range_usd"),
        "price_range_inr": prod.get("price_range_inr"),
        "current_price": float(prod.get("current_price") or 0.0),
        "compare_at_price": prod.get("compare_at_price"),
        "currency": "INR",
        "source_currency": "USD",
        "availability": "in_stock" if prod.get("availability") == "in_stock" else "out_of_stock",
        "status": prod.get("status", "ACTIVE"),
        "material": prod.get("material") or prod.get("specifications", {}).get("Material"),
        "specifications": prod.get("specifications") or {},
        "descriptionHtml": desc_html,
        "images": images,
        "variants": variants,
        "product_options": prod.get("product_options") or [],
        "tags": prod.get("tags") or [],
        "groups": prod.get("groups") or [],
        "store_display": store_display,
        "group_display": group_display,
        "subgroup_display": subgroup_display,
        "gender": prod.get("gender") or prod.get("specifications", {}).get("Gender"),
        "updated_at": prod.get("updated_at") or prod.get("last_verified_at") or "",
    }


def export_catalog(
    db_dir: str = "storage/db",
    output_dir: str = "frontend/public/data"
) -> Tuple[int, str]:
    """
    Read all partitioned product records and export catalog.json and meta.json.
    """
    os.makedirs(output_dir, exist_ok=True)
    all_products: List[Dict[str, Any]] = []
    raw_products: List[Dict[str, Any]] = []
    canonical_variant_map: Dict[str, Dict[str, Any]] = {}

    # 1. Scan store directories and read raw JSONs
    for entry in os.listdir(db_dir):
        store_path = os.path.join(db_dir, entry)
        if not os.path.isdir(store_path) or entry in ("history", "index.json"):
            continue

        products_dir = os.path.join(store_path, "products")
        if not os.path.exists(products_dir):
            continue

        for p_file in os.listdir(products_dir):
            if not p_file.endswith(".json"):
                continue
            p_path = os.path.join(products_dir, p_file)
            try:
                with open(p_path, "r", encoding="utf-8") as f:
                    prod = json.load(f)
                    raw_products.append(prod)
                    sku = prod.get("source_sku")
                    if sku:
                        canonical_variant_map[sku] = {
                            "in_stock": prod.get("availability") == "in_stock",
                            "price": str(prod.get("current_price", "")),
                            "source_price": float(prod.get("source_price") or 0.0)
                        }
            except Exception as err:
                print(f"[WARN] Failed to load {p_path}: {err}")

    # 2. Format products with canonical cross-variant reconciliation
    for prod in raw_products:
        try:
            # Ensure Level 1 Store, Level 2 Group, Level 3 Subgroup mapping
            s_store = prod.get("source_store", "").lower()
            if s_store == "jwpei":
                store_display = "JW PEI"
                group_display = "Handbags"
            elif s_store == "nordstrom":
                store_display = "Nordstrom"
                group_display = "Shoes"
            elif s_store == "michaelkors":
                store_display = "Michael Kors"
                gender = prod.get("gender", "Women")
                pt = prod.get("product_type", "Handbags")
                if gender == "Men":
                    if pt == "Shoes":
                        group_display = "Men's Shoes"
                    elif pt == "Belts":
                        group_display = "Men's Belts"
                    else:
                        group_display = "Men's Wallets"
                else:
                    if pt == "Handbags":
                        group_display = "Women's Handbags"
                    elif pt == "Wallets":
                        group_display = "Women's Wallets"
                    elif pt == "Sneakers":
                        group_display = "Women's Sneakers"
                    elif pt == "Flats":
                        group_display = "Women's Flats & Mules"
                    elif pt == "Sandals":
                        group_display = "Women's Sandals"
                    elif pt == "Boots":
                        group_display = "Women's Boots"
                    elif pt == "Sunglasses":
                        group_display = "Women's Sunglasses"
            elif s_store == "coach":
                store_display = "COACH"
                gender = prod.get("gender", "Women")
                pt = prod.get("product_type", "Handbags")
                t_chk = (prod.get("title", "") + " " + prod.get("handle", "")).lower()
                if gender == "Men":
                    if pt == "Shoes & Footwear":
                        group_display = "Men's Shoes"
                    elif pt == "Wallets & Small Goods":
                        group_display = "Men's Wallets"
                    elif pt == "Backpacks":
                        group_display = "Men's Backpacks"
                    else:
                        group_display = "Men's Bags"
                else:
                    if pt == "Shoes & Footwear":
                        group_display = "Women's Shoes"
                    elif pt == "Wristlets" and "wristlet" in t_chk:
                        group_display = "Women's Wristlets"
                    elif pt in ("Wallets & Small Goods", "Wristlets") and "wristlet" not in t_chk and any(w in t_chk for w in ["bag", "plaza"]):
                        group_display = "Women's Handbags"
                    elif pt == "Wallets & Small Goods":
                        group_display = "Women's Wallets"
                    elif pt == "Backpacks":
                        group_display = "Women's Backpacks"
                    else:
                        group_display = "Women's Handbags"
            elif s_store == "footlocker":
                store_display = "Foot Locker"
                gender = prod.get("specifications", {}).get("Gender") or prod.get("gender", "")
                if "women" in str(gender).lower() or "women" in str(prod.get("title", "")).lower():
                    group_display = "Women's Shoes"
                else:
                    group_display = "Men's Shoes"
            elif s_store == "jdsports":
                store_display = "JD Sports"
                gender = prod.get("gender") or prod.get("specifications", {}).get("Gender", "")
                sizing_cat = prod.get("sizing_category", "Adult")
                if sizing_cat in ("Grade School", "Preschool", "Toddler"):
                    group_display = "Kids' Shoes"
                elif "women" in str(gender).lower():
                    group_display = "Women's Shoes"
                else:
                    group_display = "Men's Shoes"
            else:
                store_display = prod.get("vendor", "Other")
                group_display = prod.get("product_type", "Handbags")
            subgroup_display = classify_subgroup(prod)

            formatted = format_viewer_product(
                prod,
                store_display,
                group_display,
                subgroup_display,
                canonical_variant_map=canonical_variant_map
            )
            all_products.append(formatted)
        except Exception as err:
            print(f"[WARN] Failed to format product {prod.get('id', 'unknown')}: {err}")

    # Sort products: in stock first, then by title
    all_products.sort(key=lambda p: (0 if p.get("availability") == "in_stock" else 1, p.get("title", "")))

    # 2. Compute metadata
    total = len(all_products)
    in_stock = sum(1 for p in all_products if p.get("availability") == "in_stock")
    out_of_stock = total - in_stock
    stores = sorted(list(set(p.get("store_display", "Other") for p in all_products)))
    groups = sorted(list(set(p.get("group_display", "Handbags") for p in all_products)))
    subgroups = sorted(list(set(p.get("subgroup_display", "General") for p in all_products)))

    prices_inr = [p.get("current_price", 0) for p in all_products if p.get("current_price")]
    min_price_inr = min(prices_inr) if prices_inr else 0
    max_price_inr = max(prices_inr) if prices_inr else 0

    meta = {
        "total_products": total,
        "in_stock": in_stock,
        "out_of_stock": out_of_stock,
        "stores": stores,
        "groups": groups,
        "subgroups": subgroups,
        "price_range_inr": {
            "min": min_price_inr,
            "max": max_price_inr
        },
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generated_by": "product-updater-export-pipeline"
    }

    # 3. Write catalog.json and meta.json atomically
    catalog_file = os.path.join(output_dir, "catalog.json")
    tmp_catalog = f"{catalog_file}.tmp"
    with open(tmp_catalog, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    os.replace(tmp_catalog, catalog_file)

    meta_file = os.path.join(output_dir, "meta.json")
    tmp_meta = f"{meta_file}.tmp"
    with open(tmp_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    os.replace(tmp_meta, meta_file)

    print(f"Exported {total} products to {catalog_file}")
    print(f"Metadata written to {meta_file}")
    return total, catalog_file


if __name__ == "__main__":
    count, target = export_catalog()
    print(f"Catalog export complete. Total records: {count}")
