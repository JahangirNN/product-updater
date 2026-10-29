import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getProd($handle: String!) {
  productByHandle(handle: $handle) {
    id
    title
    status
    totalVariants
    publishedAt
    variants(first: 5) {
      nodes {
        id
        title
        image { url }
      }
    }
  }
}
"""

handles = ['radio-camera-bag', 'noor-faux-suede-top-handle-bag-pink', 'keyla-weave-texture-top-handle-bag-pink']
for h in handles:
    data, ext, err = execute_shopify_graphql(query, {'handle': h})
    p = data.get('productByHandle') if data else None
    print(f"Handle: {h}")
    if p:
        print(f"  Title: {p.get('title')}")
        print(f"  Status: {p.get('status')}")
        print(f"  Published: {p.get('publishedAt')}")
        print(f"  Variants: {p.get('totalVariants')}")
        for v in p.get('variants', {}).get('nodes', []):
            img = v.get('image')
            print(f"    - {v.get('title')}: Image={'YES' if img else 'NONE'}")
    else:
        print(f"  NOT FOUND ON SHOPIFY (Error: {err})")
