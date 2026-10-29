"""
Local Database Footwear Sizing Migration Script
Standardizes existing JSON product records in:
  - storage/db/jdsports/products/
  - storage/db/footlocker/products/
  - storage/db/nordstrom/products/
Eliminates dual 'Size (US)' and 'Size (UK)' options.
Unifies to a single option 'Size' with pure UK values ('UK {size}').
Sets variant titles to 'UK {size} - {color}'.
Rebuilds storage/db/index.json.
Pure functions, zero classes (ADR 0002, ADR 0005).
"""
import os
import sys
import glob
import json
import re
from typing import Dict, Any, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.db import build_and_save_index
from storage.logger import log_info, log_success, log_warning, log_error


def normalize_variant_sizing(variant: Dict[str, Any], default_color: str = "Standard") -> Dict[str, Any]:
    """
    Transform variant option_values to single Size (pure UK) and Color.
    Update variant title to 'UK {size} - {color}'.
    """
    ovs = variant.get("option_values") or []
    
    uk_entry = next((ov for ov in ovs if isinstance(ov, dict) and "size (uk)" in ov.get("option_name", "").lower()), None)
    us_entry = next((ov for ov in ovs if isinstance(ov, dict) and "size (us)" in ov.get("option_name", "").lower()), None)
    size_entry = next((ov for ov in ovs if isinstance(ov, dict) and ov.get("option_name", "").strip().lower() == "size"), None)
    color_entry = next((ov for ov in ovs if isinstance(ov, dict) and ov.get("option_name", "").strip().lower() in ("color", "colour")), None)
    
    # Resolve pure UK size value
    uk_val = ""
    if uk_entry and uk_entry.get("name"):
        uk_val = str(uk_entry["name"]).strip()
    elif size_entry and size_entry.get("name"):
        uk_val = str(size_entry["name"]).strip()
    elif us_entry and us_entry.get("name"):
        uk_val = str(us_entry["name"]).strip()
    else:
        uk_val = str(variant.get("size") or variant.get("title") or "Standard").strip()
        
    # Format as pure UK value e.g. "UK 7" or "UK 7.5"
    if not uk_val.startswith("UK ") and not uk_val.startswith("UK"):
        m = re.search(r'UK\s*([0-9\.]+)', uk_val, re.IGNORECASE)
        if m:
            uk_val = f"UK {m.group(1)}"
        else:
            uk_val = f"UK {uk_val}"
    elif uk_val.startswith("UK") and not uk_val.startswith("UK "):
        uk_val = f"UK {uk_val[2:].strip()}"
        
    # Resolve Color value
    c_val = ""
    if color_entry and color_entry.get("name"):
        c_val = str(color_entry["name"]).strip()
    else:
        c_val = default_color or "Standard"
        
    variant["option_values"] = [
        {"option_name": "Size", "name": uk_val},
        {"option_name": "Color", "name": c_val}
    ]
    variant["title"] = f"{uk_val} - {c_val}"
    return variant


def migrate_product_dict(prod: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Migrate a single product record to unified single 'Size' option architecture.
    Returns (migrated_prod, has_changed).
    """
    variants = prod.get("variants") or []
    if not variants:
        return prod, False
        
    default_color = prod.get("color") or "Standard"
    specs = prod.get("specifications") or {}
    if not default_color or default_color == "Standard":
        default_color = specs.get("Color") or "Standard"

    # Migrate all variants
    for v in variants:
        normalize_variant_sizing(v, default_color=default_color)

    # Build unique product_options for Size and Color
    seen_sizes = set()
    size_values = []
    seen_colors = set()
    color_values = []

    for v in variants:
        for ov in v.get("option_values", []):
            if ov.get("option_name") == "Size":
                s_name = ov.get("name")
                if s_name and s_name not in seen_sizes:
                    seen_sizes.add(s_name)
                    size_values.append({"name": s_name})
            elif ov.get("option_name") == "Color":
                c_name = ov.get("name")
                if c_name and c_name not in seen_colors:
                    seen_colors.add(c_name)
                    color_values.append({"name": c_name})

    if not color_values:
        color_values = [{"name": default_color}]

    new_options = [
        {"name": "Size", "values": size_values},
        {"name": "Color", "values": color_values}
    ]

    # Deduplicate variants by unique (Size, Color) option combination
    seen_combos = {}
    deduped_variants = []
    for v in variants:
        sz_val = next((ov["name"] for ov in v.get("option_values", []) if ov.get("option_name") == "Size"), "")
        col_val = next((ov["name"] for ov in v.get("option_values", []) if ov.get("option_name") == "Color"), "")
        combo_key = (sz_val, col_val)
        if combo_key not in seen_combos:
            seen_combos[combo_key] = v
            deduped_variants.append(v)
        else:
            if v.get("in_stock") and not seen_combos[combo_key].get("in_stock"):
                seen_combos[combo_key]["in_stock"] = True
    variants = deduped_variants

    prod["variants"] = variants
    prod["product_options"] = new_options
    if "options" in prod:
        prod["options"] = new_options

    # Preserve synced status if already migrated to Shopify
    if prod.get("shopify_footwear_options_migrated") is True or prod.get("shopify_sync_pending") is False:
        prod["shopify_sync_pending"] = False
    else:
        prod["shopify_sync_pending"] = True
    return prod, True


def run_database_migration(dry_run: bool = False) -> Dict[str, int]:
    """
    Migrate all footwear products in storage/db for jdsports, footlocker, and nordstrom.
    """
    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db")
    target_stores = ["jdsports", "footlocker", "nordstrom"]

    stats = {
        "total_scanned": 0,
        "migrated": 0,
        "skipped": 0,
        "errors": 0
    }

    print("=" * 80)
    print(f"LOCAL DATABASE FOOTWEAR SIZING MIGRATION (DryRun={dry_run})")
    print(f"Target Stores: {', '.join(target_stores)}")
    print("=" * 80)

    for store in target_stores:
        pattern = os.path.join(db_root, store, "products", "*.json")
        files = glob.glob(pattern)
        log_info(f"[{store.upper()}] Found {len(files)} product files.")

        store_migrated = 0
        for fp in files:
            stats["total_scanned"] += 1
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    prod = json.load(f)

                migrated_prod, has_changed = migrate_product_dict(prod)
                if has_changed:
                    if not dry_run:
                        with open(fp, "w", encoding="utf-8") as f:
                            json.dump(migrated_prod, f, indent=2, ensure_ascii=False)
                    stats["migrated"] += 1
                    store_migrated += 1
                else:
                    stats["skipped"] += 1
            except Exception as exc:
                log_error(f"Error migrating {fp}: {exc}")
                stats["errors"] += 1

        log_success(f"[{store.upper()}] Successfully migrated {store_migrated}/{len(files)} products.")

    if not dry_run:
        log_info("Rebuilding storage/db/index.json...")
        build_and_save_index()
        log_success("storage/db/index.json successfully rebuilt.")

    print("=" * 80)
    print(f"MIGRATION COMPLETE | Scanned: {stats['total_scanned']} | Migrated: {stats['migrated']} | Errors: {stats['errors']}")
    print("=" * 80)
    return stats


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    run_database_migration(dry_run=is_dry)
