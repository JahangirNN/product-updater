"""
Catalog Reprocessor & Enhancement Script
Applies improved dimension keys ('Dimension', 'Dimensions', 'Bag Dimensions'),
material fallback ('Main Material', 'Major Material', 'Material'), and typography fixes
across all 288 local partitioned JSON files in storage/db/jwpei/products/.
Pure functions, zero classes (ADR 0005).
"""
import os
import sys
import json
import re
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.db import save_product, build_and_save_index
from stores.jwpei.inflow import generate_description_html


def reprocess_all_products(products_dir: str = "storage/db/jwpei/products"):
    print("=" * 65)
    print("REPROCESSING CATALOG WITH IMPROVED SPECS & SIZE GUIDES")
    print("=" * 65)

    if not os.path.exists(products_dir):
        print(f"Error: {products_dir} does not exist.")
        return

    file_names = [f for f in os.listdir(products_dir) if f.endswith(".json")]
    total = len(file_names)
    print(f"Found {total} products to reprocess.")

    updated_count = 0
    dims_found = 0
    materials_updated = 0

    t0 = time.perf_counter()

    for f_name in file_names:
        f_path = os.path.join(products_dir, f_name)
        with open(f_path, "r", encoding="utf-8") as f:
            product = json.load(f)

        specs = product.get("specifications", {})
        
        # 1. Clean spacing on all spec values
        cleaned_specs = {}
        for k, v in specs.items():
            clean_k = k.strip()
            clean_v = re.sub(r'\s+"', '"', str(v).strip()) if isinstance(v, str) else v
            cleaned_specs[clean_k] = clean_v

        # 2. Extract Bag Dimensions (checking all key variations)
        dim_val = (
            cleaned_specs.get("Bag Dimensions") or 
            cleaned_specs.get("Dimension") or 
            cleaned_specs.get("Dimensions") or
            cleaned_specs.get("Bag Dimension")
        )
        if dim_val and dim_val != "N/A":
            cleaned_specs["Bag Dimensions"] = dim_val
            dims_found += 1

        # 3. Extract Material (checking Main Material, Major Material, Material)
        mat_val = (
            cleaned_specs.get("Material") or 
            cleaned_specs.get("Main Material") or 
            cleaned_specs.get("Major Material") or 
            "Vegan Leather"
        )
        if mat_val != product.get("material"):
            materials_updated += 1
        cleaned_specs["Material"] = mat_val
        product["material"] = mat_val
        product["specifications"] = cleaned_specs

        # 4. Regenerate clean descriptionHtml with complete size guide table
        body_html = product.get("descriptionHtml", "")
        new_desc_html = generate_description_html(body_html, cleaned_specs)
        product["descriptionHtml"] = new_desc_html

        # 5. Save atomically
        save_product(product)
        updated_count += 1

    # 6. Rebuild global index
    print("\nUpdating storage/db/index.json...")
    build_and_save_index()

    dur = time.perf_counter() - t0
    print("\n" + "=" * 65)
    print("CATALOG ENHANCEMENT SUMMARY")
    print("=" * 65)
    print(f"Products Reprocessed:       {updated_count} / {total}")
    print(f"Valid Dimensions in Table:  {dims_found} / {total} ({dims_found/total*100:.1f}%)")
    print(f"Material Discrepancies Fixed: {materials_updated} products")
    print(f"Time Taken:                 {dur:.2f} seconds")
    print("=" * 65)


if __name__ == "__main__":
    reprocess_all_products()
