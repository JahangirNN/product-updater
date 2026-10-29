import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

handles = [
    'coach', 'michael-kors', 'jw-pei', 'tissot', 'seiko', 'citizen',
    'movado', 'versace', 'nike', 'on-running', 'hoka', 'salomon',
    'wallets-leather-goods', 'womens-sunglasses', 'mens-sunglasses',
    'totes', 'crossbody-bags', 'designer-bags', 'premium-footwear',
    'luxury-watches', 'instant-ship', 'ready-to-ship'
]

query = """
query GetCol($handle: String!) {
  collectionByHandle(handle: $handle) {
    id
    handle
    image {
      url
    }
  }
}
"""
missing = []
for h in handles:
    res, _, _ = execute_shopify_graphql(query, {'handle': h})
    col = res.get('collectionByHandle') if res else None
    if not col:
        print(f"{h:25}: NOT FOUND")
    else:
        img = col.get('image')
        if img:
            print(f"{h:25}: YES -> {img['url'][:60]}")
        else:
            print(f"{h:25}: MISSING IMAGE")
            missing.append(h)

print("\nTotal missing:", len(missing), missing)
