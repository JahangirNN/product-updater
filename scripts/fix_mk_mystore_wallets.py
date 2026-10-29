import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

handles = [
    "cooper-logo-billfold-wallet-with-passcase",
    "cooper-signature-billfold-wallet",
    "michael-kors-logo-print-wallet-belt-gift-set",
    "jet-set-travel-small-signature-logo-and-smooth-wristlet",
    "jet-set-travel-small-signature-logo-and-smooth-wristlet-1",
    "jet-set-travel-striped-signature-logo-convertible-wristlet",
]

PRODUCT_UPDATE = """
mutation updateProduct($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
      vendor
      tags
    }
    userErrors {
      field
      message
    }
  }
}
"""

for h in handles:
    q = f"""
    query {{
      productByHandle(handle: "{h}") {{
        id
        title
        vendor
        tags
      }}
    }}
    """
    d, _, err = execute_shopify_graphql(q, allow_retry=False)
    p = d.get("productByHandle") if d else None
    if p:
        pid = p["id"]
        title = p["title"]
        current_vendor = p["vendor"]
        current_tags = list(p.get("tags") or [])
        print(f"Product: {title} | Current Vendor: {current_vendor}")
        
        # New tags
        needed_tags = list(set(current_tags + [
            "Ready to Ship", "instant-ship", "Michael Kors", "MICHAEL Michael Kors",
            "Brand:MICHAEL Michael Kors", "Wallets & Small Leather Goods", "Wallets",
            "Wallets & Accessories", "Accessories"
        ]))
        
        up_payload = {
            "id": pid,
            "vendor": "MICHAEL Michael Kors",
            "productType": "Wallets & Small Leather Goods",
            "tags": needed_tags
        }
        res_up, _, err_up = execute_shopify_graphql(PRODUCT_UPDATE, variables={"input": up_payload}, allow_retry=False)
        print("Updated:", res_up)
