import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from collections import Counter

query = """
query getCollectionTags($handle: String!) {
  collectionByHandle(handle: $handle) {
    id
    title
    handle
    products(first: 50) {
      edges {
        node {
          id
          title
          vendor
          tags
        }
      }
    }
  }
}
"""

for col_handle in ["womens-handbags", "designer-bags", "luxury-bags"]:
    data, ext, err = execute_shopify_graphql(query, {"handle": col_handle})
    if data and data.get("collectionByHandle"):
        col = data["collectionByHandle"]
        tag_counter = Counter()
        vendor_counter = Counter()
        prods = col.get("products", {}).get("edges", [])
        for p in prods:
            node = p["node"]
            vendor_counter[node["vendor"]] += 1
            for t in node.get("tags", []):
                tag_counter[t] += 1
        print(f"=== Collection: {col['title']} ({col_handle}) ===")
        print(f"Products sampled: {len(prods)}")
        print(f"Vendors: {dict(vendor_counter)}")
        print(f"Top 20 Tags: {tag_counter.most_common(20)}")
        print()
    else:
        print(f"Error fetching {col_handle}: {err}")
