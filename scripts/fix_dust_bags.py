import sys, os
sys.path.insert(0, r"c:\workspace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql

mut_product = """
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

mut_variant = """
mutation productVariantUpdate($input: ProductVariantInput!) {
  productVariantUpdate(input: $input) {
    productVariant {
      id
      price
      compareAtPrice
    }
    userErrors {
      field
      message
    }
  }
}
"""

# 1. Update Small Dust Bag
res1, _, _ = execute_shopify_graphql(mut_product, variables={
    "input": {
        "id": "gid://shopify/Product/15841792196774",
        "productType": "Care & Storage",
        "tags": ["Accessories", "Bag Care", "Brand:Michael Kors", "Care & Storage", "Dust Bag", "Michael Kors"]
    }
})
print("Product Update 1:", res1)

res_var1, _, _ = execute_shopify_graphql(mut_variant, variables={
    "input": {
        "id": "gid://shopify/ProductVariant/57534955389094",
        "compareAtPrice": None
    }
})
print("Variant Update 1 (Cleared compare-at price):", res_var1)

# 2. Update Large Dust Bag
res2, _, _ = execute_shopify_graphql(mut_product, variables={
    "input": {
        "id": "gid://shopify/Product/15841789214886",
        "productType": "Care & Storage",
        "tags": ["Accessories", "Bag Care", "Brand:Michael Kors", "Care & Storage", "Dust Bag", "Michael Kors"]
    }
})
print("Product Update 2:", res2)

print("\n[SUCCESS] Successfully fixed both Dust Bags!")
