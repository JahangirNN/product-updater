import os
import sys
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

PRODUCT_UPDATE_MUTATION = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

def draft_zero_image_products():
    print("=" * 80)
    print("ENFORCING ZERO-IMAGE RULE: DRAFTING ALL ZERO-IMAGE PRODUCTS ON SHOPIFY")
    print("=" * 80)

    json_path = os.path.join(PROJECT_ROOT, "storage", "zero_image_products.json")
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found!")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    active_zero_image = [p for p in products if p.get("status") == "ACTIVE"]

    print(f"Total zero-image products: {len(products)}")
    print(f"Currently ACTIVE zero-image products to DRAFT: {len(active_zero_image)}")

    drafted = []
    errors = []

    for i, p in enumerate(active_zero_image, 1):
        pid = p["id"]
        title = p["title"]
        print(f"[{i}/{len(active_zero_image)}] Drafting {p['vendor']} - {title[:50]} ({pid})...")

        variables = {
            "input": {
                "id": pid,
                "status": "DRAFT"
            }
        }
        res_data, resp, err = execute_shopify_graphql(PRODUCT_UPDATE_MUTATION, variables=variables)

        if err:
            print(f"  ❌ Error: {err}")
            errors.append({"id": pid, "error": str(err)})
            continue

        p_res = res_data.get("productUpdate", {})
        user_errors = p_res.get("userErrors", [])
        if user_errors:
            print(f"  ❌ GraphQL userErrors: {user_errors}")
            errors.append({"id": pid, "userErrors": user_errors})
        else:
            updated_product = p_res.get("product", {})
            print(f"  ✅ Drafted successfully! Status: {updated_product.get('status')}")
            drafted.append(pid)
            p["status"] = "DRAFT"

        time.sleep(0.3)

    print("\n" + "=" * 80)
    print(f"DRAFTING COMPLETE: {len(drafted)} products transitioned to DRAFT status.")
    if errors:
        print(f"ERRORS: {len(errors)} products failed.")
    print("=" * 80)

    # Update zero_image_products.json with new statuses
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return drafted, errors

if __name__ == "__main__":
    draft_zero_image_products()
