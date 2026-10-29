import os
import sys
import json
import glob
from typing import Dict, Any, List, Tuple, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import resolve_luxury_bag_silhouette, resolve_product_type, resolve_gender, resolve_authentic_vendor

def resolve_options_and_variants_v2(
    prod: Dict[str, Any],
    forex_rate: Optional[float] = None,
    source_price: float = 0.0,
    compare_source: Optional[float] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if forex_rate is None:
        forex_rate = 83.5

    variants_raw = prod.get("variants") or []
    source_sku = prod.get("source_sku") or prod.get("sku") or prod.get("id") or ""
    product_type = resolve_product_type(prod)
    bag_sil = resolve_luxury_bag_silhouette(prod)

    # 1. Fallback for zero variants or empty variant list
    if not variants_raw:
        inr_price = float(round(source_price * forex_rate))
        compare_str = None
        if compare_source and float(compare_source) > source_price:
            compare_str = f"{float(round(float(compare_source) * forex_rate)):.2f}"

        sku_val = f"RARE-{source_sku}" if source_sku and not str(source_sku).startswith("RARE-") else (source_sku or "")
        return (
            [{"name": "Title", "values": [{"name": "Default Title"}]}],
            [{
                "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                "price": f"{inr_price:.2f}",
                "compareAtPrice": compare_str,
                "sku": sku_val,
                "inventoryPolicy": "DENY"
            }]
        )

    # 2. Discover all option dimension names in order of appearance
    ordered_dim_names: List[str] = []
    for v in variants_raw:
        if not isinstance(v, dict):
            continue
        ovs = v.get("option_values")
        if isinstance(ovs, list) and len(ovs) > 0:
            for ov in ovs:
                if isinstance(ov, dict):
                    raw_name = ov.get("option_name") or ""
                    clean_name = "Color" if raw_name.strip() in ("Color", "Colour") else raw_name.strip()
                    if clean_name and clean_name not in ordered_dim_names:
                        ordered_dim_names.append(clean_name)

    # If no option_values or option names discovered, infer from product attributes
    if not ordered_dim_names:
        has_color = any(v.get("color") for v in variants_raw if isinstance(v, dict))
        has_size = any(v.get("size") for v in variants_raw if isinstance(v, dict))
        if has_color and has_size:
            ordered_dim_names = ["Size", "Color"]
        elif has_color:
            ordered_dim_names = ["Color"]
        elif has_size:
            ordered_dim_names = ["Size"]
        elif product_type == "Watches":
            ordered_dim_names = ["Case Diameter"]
        elif product_type in ("Shoes", "Sneakers", "Sandals", "Boots", "Flats"):
            ordered_dim_names = ["Size"]
        elif bag_sil:
            ordered_dim_names = ["Color"]
        else:
            ordered_dim_names = ["Option"]

    # Limit to maximum 3 options (Shopify GraphQL limit)
    ordered_dim_names = ordered_dim_names[:3]

    # 3. Extract and deduplicate variant rows
    # key: tuple of dimension values e.g. ("US 6 / UK 4", "Black")
    seen_variants: Dict[Tuple[str, ...], Tuple[Dict[str, Any], List[Dict[str, str]]]] = {}
    dim_values_set: Dict[str, set] = {d: set() for d in ordered_dim_names}

    for v in variants_raw:
        if not isinstance(v, dict):
            continue

        var_opt_map: Dict[str, str] = {}
        # Parse from option_values if present
        if isinstance(v.get("option_values"), list):
            for ov in v["option_values"]:
                if isinstance(ov, dict):
                    on = "Color" if ov.get("option_name", "").strip() in ("Color", "Colour") else ov.get("option_name", "").strip()
                    if on:
                        var_opt_map[on] = str(ov.get("name") or "").strip()[:40]

        # Fill any missing dimensions from variant fields
        row_values: List[str] = []
        opt_val_list: List[Dict[str, str]] = []

        for d in ordered_dim_names:
            val = var_opt_map.get(d)
            if not val:
                if d == "Color":
                    val = str(v.get("color") or (v.get("title") if not v.get("size") else "") or "Default").strip()[:40]
                elif d == "Size":
                    val = str(v.get("size") or v.get("title") or "Standard").strip()[:40]
                else:
                    val = str(v.get("title") or "Default").strip()[:40]
            if not val:
                val = "Default"

            row_values.append(val)
            dim_values_set[d].add(val)
            opt_val_list.append({"optionName": d, "name": val})

        row_key = tuple(row_values)
        if row_key not in seen_variants:
            seen_variants[row_key] = (v, opt_val_list)
        else:
            # If current variant is in stock and existing is not, prioritize current
            existing_v = seen_variants[row_key][0]
            if existing_v.get("availability") != "in_stock" and not existing_v.get("in_stock") and (v.get("availability") == "in_stock" or v.get("in_stock")):
                seen_variants[row_key] = (v, opt_val_list)

    # 4. Construct ProductSet variant inputs
    variant_inputs: List[Dict[str, Any]] = []
    for row_key, (v, opt_val_list) in seen_variants.items():
        v_source_price = float(v.get("source_price") or prod.get("source_price") or source_price or 0.0)
        v_inr_price = float(round(v_source_price * forex_rate))

        v_compare_source = v.get("source_compare_at_price") or compare_source
        v_compare_str = None
        if v_compare_source and float(v_compare_source) > v_source_price:
            v_compare_str = f"{float(round(float(v_compare_source) * forex_rate)):.2f}"

        v_sku = v.get("sku") or source_sku or ""
        if v_sku and not v_sku.startswith("RARE-"):
            v_sku = f"RARE-{v_sku}"

        v_img = v.get("image_url") or v.get("image") or (v.get("images") or [None])[0]
        v_barcode = v.get("barcode") or v.get("upc") or v.get("ean")

        var_dict = {
            "optionValues": opt_val_list,
            "price": f"{v_inr_price:.2f}",
            "compareAtPrice": v_compare_str,
            "sku": v_sku,
            "inventoryPolicy": "DENY"
        }
        if v_img and isinstance(v_img, str) and v_img.startswith("http"):
            var_dict["file"] = {
                "originalSource": v_img,
                "contentType": "IMAGE"
            }
        if v_barcode:
            var_dict["barcode"] = str(v_barcode).strip()

        variant_inputs.append(var_dict)

    # 5. Build productOptions list
    product_options = []
    for d in ordered_dim_names:
        sorted_vals = sorted(list(dim_values_set[d]))
        product_options.append({
            "name": d,
            "values": [{"name": val} for val in sorted_vals]
        })

    return product_options, variant_inputs

# Quick test on MK sandal
with open("storage/db/michaelkors/products/0033a8e4440e7c16.json", "r", encoding="utf-8") as f:
    mk_sandal = json.load(f)

opts, vars = resolve_options_and_variants_v2(mk_sandal)
print("MK Sandal options:", opts)
print(f"MK Sandal variants count: {len(vars)}")
for v in vars[:2]:
    print("  ", v["sku"], v["optionValues"])
