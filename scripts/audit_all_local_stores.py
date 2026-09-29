import os
import sys
import glob
import json
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

stores = ["jwpei", "coach", "michaelkors", "jomashop", "nordstrom", "footlocker", "jdsports"]

stats = {
    "by_store": {},
    "missing_cases": {
        "case_a_has_image_unlinked": 0, # variant in local JSON has image_url/image/images
        "case_b_null_in_local": 0,       # variant in local JSON has null/empty image
        "case_c_gallery_matchable": 0,   # no variant image, but matches gallery image
        "case_d_ghost_no_image": 0       # no image anywhere
    }
}

sample_cases = defaultdict(list)

for store in stores:
    pattern = os.path.join(PROJECT_ROOT, "storage", "db", store, "products", "*.json")
    files = glob.glob(pattern)
    store_stats = {
        "total_files": len(files),
        "synced_to_shopify": 0,
        "multi_variant_products": 0,
        "total_variants": 0,
        "variants_with_image": 0,
        "variants_without_image": 0,
        "color_variants_without_image": 0
    }
    
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            continue
            
        is_synced = bool(data.get("shopify_product_id"))
        if is_synced:
            store_stats["synced_to_shopify"] += 1
            
        variants = data.get("variants") or []
        gallery = data.get("images") or []
        gallery_str = " ".join([str(img).lower() for img in gallery if isinstance(img, str)])
        
        if len(variants) > 1:
            store_stats["multi_variant_products"] += 1
            
        for v in variants:
            if not isinstance(v, dict):
                continue
            store_stats["total_variants"] += 1
            
            v_img = v.get("image_url") or v.get("image") or (v.get("images") or [None])[0]
            v_color = v.get("color") or v.get("title") or ""
            is_color = bool(v.get("color") or ("color" in str(v.get("option_values")).lower()))
            
            if v_img:
                store_stats["variants_with_image"] += 1
                if is_synced:
                    stats["missing_cases"]["case_a_has_image_unlinked"] += 1
            else:
                store_stats["variants_without_image"] += 1
                if is_color:
                    store_stats["color_variants_without_image"] += 1
                
                # Check if gallery matches colorway
                color_norm = str(v_color).lower().strip().replace(" ", "-").replace("/", "-")
                matched_gallery = False
                for g_img in gallery:
                    if isinstance(g_img, str) and color_norm and color_norm in g_img.lower():
                        matched_gallery = True
                        break
                
                if matched_gallery:
                    stats["missing_cases"]["case_c_gallery_matchable"] += 1
                    if len(sample_cases["case_c"]) < 5:
                        sample_cases["case_c"].append({
                            "store": store,
                            "handle": data.get("handle"),
                            "variant": v_color,
                            "gallery_sample": gallery[:3]
                        })
                elif len(gallery) > 0:
                    stats["missing_cases"]["case_b_null_in_local"] += 1
                    if len(sample_cases["case_b"]) < 5:
                        sample_cases["case_b"].append({
                            "store": store,
                            "handle": data.get("handle"),
                            "variant": v_color,
                            "gallery_count": len(gallery)
                        })
                else:
                    stats["missing_cases"]["case_d_ghost_no_image"] += 1
                    if len(sample_cases["case_d"]) < 5:
                        sample_cases["case_d"].append({
                            "store": store,
                            "handle": data.get("handle"),
                            "variant": v_color
                        })
                        
    stats["by_store"][store] = store_stats

print("=" * 80)
print("LOCAL CATALOG FORENSIC AUDIT SUMMARY")
print("=" * 80)
for store, s in stats["by_store"].items():
    print(f"STORE: {store.upper():12} | Files: {s['total_files']:5} | Synced: {s['synced_to_shopify']:5} | Multi-var Prods: {s['multi_variant_products']:5} | Vars: {s['total_variants']:6} | Vars w/ img: {s['variants_with_image']:6} | Vars w/o img: {s['variants_without_image']:5} | Color vars w/o img: {s['color_variants_without_image']}")

print("\n" + "=" * 80)
print("MISSING IMAGE CASE BREAKDOWN:")
print("=" * 80)
print(f"Case (a) - Local record HAS variant image, but unlinked in Shopify: {stats['missing_cases']['case_a_has_image_unlinked']}")
print(f"Case (b) - Local variant has null image, but parent has gallery:    {stats['missing_cases']['case_b_null_in_local']}")
print(f"Case (c) - Variant image missing, matchable in gallery:            {stats['missing_cases']['case_c_gallery_matchable']}")
print(f"Case (d) - Ghost variant, no authentic image anywhere:             {stats['missing_cases']['case_d_ghost_no_image']}")

out_path = os.path.join(PROJECT_ROOT, "storage", "local_catalog_forensic_audit.json")
with open(out_path, "w", encoding="utf-8") as fp:
    json.dump({
        "stats": stats,
        "sample_cases": dict(sample_cases)
    }, fp, indent=2)
print(f"\nSaved report to: {out_path}")
