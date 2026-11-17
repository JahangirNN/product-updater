import sys, os, json
sys.path.insert(0, r"c:\workspace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql

PRODUCT_ID = "gid://shopify/Product/15851463016614"

# 1. Inspect
query_inspect = """
query {
  product(id: "gid://shopify/Product/15851463016614") {
    id
    title
    productType
    tags
    options {
      name
      values
    }
  }
}
"""
res, _, _ = execute_shopify_graphql(query_inspect)
p = res.get("product", {})
print("Current Product:", p.get("title"))
print("Current Type:", p.get("productType"))
print("Current Tags:", p.get("tags"))

# 2. Clean tags: remove Footwear, Shoes, Premium Footwear
current_tags = p.get("tags", [])
cleaned_tags = [t for t in current_tags if t not in ["Footwear", "Shoes", "Premium Footwear"]]
if "Apparel" not in cleaned_tags: cleaned_tags.append("Apparel")
if "Clothing" not in cleaned_tags: cleaned_tags.append("Clothing")
if "Swimwear" not in cleaned_tags: cleaned_tags.append("Swimwear")

mutation_update = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
      productType
      tags
    }
    userErrors {
      field
      message
    }
  }
}
"""

res_update, _, err = execute_shopify_graphql(mutation_update, variables={
    "input": {
        "id": PRODUCT_ID,
        "productType": "Apparel",
        "tags": cleaned_tags
    }
})

if err or (res_update and res_update.get("productUpdate", {}).get("userErrors")):
    print("Error updating product:", err, res_update.get("productUpdate", {}).get("userErrors"))
else:
    updated = res_update["productUpdate"]["product"]
    print("\n[SUCCESS] Successfully updated product!")
    print("New Type:", updated["productType"])
    print("New Tags:", updated["tags"])
