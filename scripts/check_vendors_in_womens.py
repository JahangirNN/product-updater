import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from collections import Counter

query = """
query getVendorCounts {
  collectionByHandle(handle: "womens-handbags") {
    products(first: 250) {
      pageInfo {
        hasNextPage
        endCursor
      }
      edges {
        node {
          title
          vendor
          tags
        }
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
if data:
    edges = data['collectionByHandle']['products']['edges']
    vendors = Counter(e['node']['vendor'] for e in edges)
    print(f"Sampled {len(edges)} products in womens-handbags:")
    print("Vendors:", dict(vendors))
    
    # Check if coach is present
    coach_prods = [e['node'] for e in edges if 'coach' in e['node']['vendor'].lower()]
    print("Coach products in sample:", len(coach_prods))
    if coach_prods:
        print("Sample coach tags:", coach_prods[0]['tags'])
        
    # Check crossbody products
    cb_prods = [e['node'] for e in edges if any('crossbody' in t.lower() for t in e['node']['tags'])]
    print("Crossbody products in sample:", len(cb_prods))
    if cb_prods:
        print("Sample cb tags:", [t for t in cb_prods[0]['tags'] if 'crossbody' in t.lower()])
