import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()

query = """
query getProductNode($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    onlineStoreUrl
  }
}
"""

for brand in ["coach", "jwpei", "michaelkors"]:
    print(f"=== {brand.upper()} HANDLES IN SHOPIFY ===")
    prods = [p for p in catalog[brand] if p.get("shopify_product_id")]
    for p in prods[:3]:
        sp_id = p["shopify_product_id"]
        local_handle = p.get("shopify_handle") or p.get("handle")
        data, ext, err = execute_shopify_graphql(query, {"id": sp_id})
        if data and data.get("product"):
            prod_node = data["product"]
            print(f"Title: {prod_node['title']}")
            print(f"  Local Handle:   {local_handle}")
            print(f"  Shopify Handle: {prod_node['handle']}")
            print(f"  Shopify Status: {prod_node['status']}")
            print(f"  OnlineStoreUrl: {prod_node.get('onlineStoreUrl')}")
        else:
            print(f"Error fetching {sp_id}: {err}")
