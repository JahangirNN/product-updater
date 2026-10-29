"""
Script: scripts/remove_availability_from_descriptions.py
Purpose: Removes the static 'Availability' column (In Stock / Out of Stock / Sold Out)
from the size guide accordion table in descriptionHtml across all 1,021 footwear products.
Updates both local JSON database files and live Shopify Admin via GraphQL productUpdate.
"""
import os
import sys
import json
import glob
import re
import time
from typing import List, Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_auth import execute_shopify_graphql

PRODUCT_UPDATE_MUTATION = """
mutation updateProductDescription($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
    }
    userErrors {
      field
      message
    }
  }
}
"""


def clean_description_html(html_str: str) -> str:
    """Strip Availability table header and data cells from size-guide-accordion."""
    if not html_str or "size-guide" not in html_str:
        return html_str

    # 1. Strip <th...>Availability</th>
    cleaned = re.sub(r'<th[^>]*>\s*Availability\s*</th>\s*', '', html_str, flags=re.IGNORECASE)

    # 2. Strip <td...>(In Stock|Out of Stock|Sold Out)</td>
    cleaned = re.sub(r'<td[^>]*>\s*(?:In Stock|Out of Stock|Sold Out)\s*</td>\s*', '', cleaned, flags=re.IGNORECASE)

    return cleaned


def main():
    print("=" * 80)
    print("CLEANING SIZE GUIDE TABLES: REMOVING 'AVAILABILITY' COLUMN")
    print("=" * 80)

    stores = ["jdsports", "footlocker", "nordstrom"]
    total_cleaned_local = 0
    total_pushed_shopify = 0
    total_errors = 0

    for store in stores:
        store_dir = os.path.join(PROJECT_ROOT, "storage", "db", store, "products")
        json_files = glob.glob(os.path.join(store_dir, "*.json"))
        print(f"\nProcessing {store.upper()} ({len(json_files)} products)...")

        cleaned_in_store = 0
        pushed_in_store = 0

        for idx, file_path in enumerate(json_files, 1):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    prod = json.load(f)

                desc = prod.get("descriptionHtml") or prod.get("description_html") or prod.get("body_html") or ""
                if not ("Availability" in desc and "size-guide" in desc):
                    continue

                cleaned_desc = clean_description_html(desc)
                if cleaned_desc == desc:
                    continue

                # Update in local JSON
                prod["descriptionHtml"] = cleaned_desc
                if "description_html" in prod:
                    prod["description_html"] = cleaned_desc
                if "body_html" in prod:
                    prod["body_html"] = cleaned_desc

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(prod, f, indent=2, ensure_ascii=False)

                cleaned_in_store += 1
                total_cleaned_local += 1

                # Push to Shopify if GID exists
                gid = prod.get("shopify_product_id")
                if gid:
                    variables = {
                        "input": {
                            "id": gid,
                            "descriptionHtml": cleaned_desc
                        }
                    }
                    res, cost, err = execute_shopify_graphql(PRODUCT_UPDATE_MUTATION, variables)
                    user_errors = res.get("productUpdate", {}).get("userErrors", []) if res else []

                    if err or user_errors:
                        print(f"  [ERR] {store} {prod.get('handle', gid)}: {err or user_errors}")
                        total_errors += 1
                    else:
                        pushed_in_store += 1
                        total_pushed_shopify += 1

                    # Polite rate limit: ~10 requests/sec
                    time.sleep(0.1)

                if idx % 50 == 0 or idx == len(json_files):
                    print(f"  Progress {store.upper()}: {idx}/{len(json_files)} scanned | Cleaned local: {cleaned_in_store} | Pushed Shopify: {pushed_in_store}")

            except Exception as e:
                print(f"  [EXCEPTION] {file_path}: {e}")
                total_errors += 1

        print(f"Completed {store.upper()}: Cleaned Local = {cleaned_in_store}, Pushed to Shopify = {pushed_in_store}")

    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print(f"Total Local JSON Files Cleaned:    {total_cleaned_local}")
    print(f"Total Shopify Products Updated:   {total_pushed_shopify}")
    print(f"Total Errors Encountered:         {total_errors}")
    print("=" * 80)


if __name__ == "__main__":
    main()
