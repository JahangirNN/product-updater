import os
import sys
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getProducts($cursor: String) {
  products(first: 100, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      title
      handle
      vendor
      productType
      status
      totalVariants
      options {
        name
        values
      }
      variants(first: 50) {
        nodes {
          id
          title
          selectedOptions {
            name
            value
          }
          image {
            id
            url
          }
        }
      }
    }
  }
}
"""

all_products = []
cursor = None
page = 1

print("Fetching all live Shopify products...")
while True:
    data, ext, err = execute_shopify_graphql(query, {"cursor": cursor})
    if err or not data:
        print(f"Error fetching page {page}: {err}")
        break
    
    prod_data = data.get("products", {})
    nodes = prod_data.get("nodes", [])
    all_products.extend(nodes)
    print(f"Page {page}: fetched {len(nodes)} products (Total: {len(all_products)})")
    
    page_info = prod_data.get("pageInfo", {})
    if page_info.get("hasNextPage"):
        cursor = page_info.get("endCursor")
        page += 1
        time.sleep(0.2)
    else:
        break

print(f"\nTotal live products on Shopify: {len(all_products)}")

# Detailed Variant Image Analysis
prods_with_missing_var_imgs = []
total_variants = 0
variants_missing_image = 0
color_variants_missing_image = 0

for p in all_products:
    p_id = p["id"]
    handle = p["handle"]
    title = p["title"]
    vendor = p["vendor"]
    status = p["status"]
    options = p.get("options") or []
    has_color_opt = any(o.get("name", "").lower() in ["color", "colour"] for o in options)
    
    variants = p.get("variants", {}).get("nodes", [])
    total_variants += len(variants)
    
    missing_in_this_prod = []
    for v in variants:
        v_id = v["id"]
        v_title = v["title"]
        v_img = v.get("image")
        
        # Check if color is involved
        sel_opts = {so["name"].lower(): so["value"] for so in v.get("selectedOptions", [])}
        is_color = "color" in sel_opts or "colour" in sel_opts or (has_color_opt and v_title != "Default Title")
        
        if not v_img:
            variants_missing_image += 1
            if is_color or has_color_opt:
                color_variants_missing_image += 1
            missing_in_this_prod.append({
                "variant_id": v_id,
                "variant_title": v_title,
                "selected_options": sel_opts,
                "is_color": is_color
            })
            
    if missing_in_this_prod:
        prods_with_missing_var_imgs.append({
            "id": p_id,
            "handle": handle,
            "title": title,
            "vendor": vendor,
            "status": status,
            "has_color_option": has_color_opt,
            "total_variants": len(variants),
            "missing_variants_count": len(missing_in_this_prod),
            "missing_variants": missing_in_this_prod
        })

print("\n" + "=" * 80)
print("LIVE SHOPIFY CATALOG VARIANT IMAGE AUDIT REPORT")
print("=" * 80)
print(f"Total Products Analyzed: {len(all_products)}")
print(f"Total Variants Analyzed: {total_variants}")
print(f"Total Variants with Missing Image: {variants_missing_image}")
print(f"Color Variants with Missing Image: {color_variants_missing_image}")
print(f"Products Affected: {len(prods_with_missing_var_imgs)}")

# Breakdown by vendor
by_vendor = {}
for p in prods_with_missing_var_imgs:
    v = p["vendor"] or "Unknown"
    by_vendor[v] = by_vendor.get(v, 0) + 1

print("\nAffected Products by Vendor:")
for v, count in sorted(by_vendor.items(), key=lambda x: x[1], reverse=True):
    print(f"  - {v}: {count} products")

out_file = os.path.join(PROJECT_ROOT, "storage", "live_missing_variant_images_audit.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump({
        "total_products": len(all_products),
        "total_variants": total_variants,
        "variants_missing_image": variants_missing_image,
        "color_variants_missing_image": color_variants_missing_image,
        "affected_products_count": len(prods_with_missing_var_imgs),
        "affected_by_vendor": by_vendor,
        "affected_products": prods_with_missing_var_imgs
    }, f, indent=2)

print(f"\nAudit results written to: {out_file}")
