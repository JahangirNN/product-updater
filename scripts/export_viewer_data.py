"""
Catalog Data Exporter for Frontend Viewer
Reads partitioned local JSON database and compiles static JSON bundles for GitHub Pages.
Pure functions, zero classes (ADR 0004, ADR 0005).
"""
import os
import sys
import json
import time
from typing import Dict, Any, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def classify_subgroup(product: Dict[str, Any]) -> str:
    """
    Classify product into Level 3 Subgroup based on title and specifications.
    Supports both JW PEI Handbags and Nordstrom On Footwear.
    """
    title_lower = product.get("title", "").lower()
    handle_lower = product.get("handle", "").lower()
    specs = product.get("specifications", {})
    source_store = product.get("source_store", "").lower()
    groups = [g.lower() for g in product.get("groups", [])]

    # Footwear taxonomy for Nordstrom / On Running
    if source_store == "nordstrom" or "shoes" in groups or "footwear" in product.get("tags", []):
        if "waterproof" in title_lower or "waterproof" in handle_lower:
            return "Waterproof Footwear"
        elif "trail" in title_lower or "hiking" in title_lower or "hike" in handle_lower:
            return "Trail & Outdoor"
        elif "roger" in title_lower or "tennis" in title_lower or "court" in title_lower:
            return "Tennis & Court"
        elif "training" in title_lower or "pulse" in title_lower or "cloud x" in title_lower:
            return "Training & Gym"
        elif "mule" in title_lower or "slide" in title_lower:
            return "Mules & Slides"
        elif "surfer" in title_lower or "runner" in title_lower or "monster" in title_lower or "running" in title_lower or "boom" in title_lower:
            return "Running Shoes"
        elif "coast" in title_lower or "nova" in title_lower or "tilt" in title_lower or "sneaker" in title_lower:
            return "Lifestyle & Casual"
        return "Performance Footwear"

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


def export_catalog(
    db_dir: str = "storage/db",
    output_dir: str = "frontend/public/data"
) -> Tuple[int, str]:
    """
    Read all partitioned product records and export catalog.json and meta.json.
    """
    os.makedirs(output_dir, exist_ok=True)
    all_products: List[Dict[str, Any]] = []

    # 1. Scan store directories
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

                # Ensure Level 1 Store, Level 2 Group, Level 3 Subgroup mapping
                s_store = prod.get("source_store", "").lower()
                if s_store == "jwpei":
                    store_display = "JW PEI"
                elif s_store == "nordstrom":
                    store_display = "Nordstrom"
                else:
                    store_display = prod.get("vendor", "Other")

                groups = prod.get("groups", ["Handbags"])
                group_display = groups[0].capitalize() if groups else "Handbags"
                subgroup_display = classify_subgroup(prod)

                prod["store_display"] = store_display
                prod["group_display"] = group_display
                prod["subgroup_display"] = subgroup_display

                all_products.append(prod)
            except Exception as err:
                print(f"[WARN] Failed to load {p_path}: {err}")

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
