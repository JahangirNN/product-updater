import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getColRule($handle: String!) {
  collectionByHandle(handle: $handle) {
    id
    title
    handle
    productsCount {
      count
    }
    ruleSet {
      appliedDisjunctively
      rules {
        column
        relation
        condition
      }
    }
  }
}
"""

for h in ['womens-handbags', 'mens-bags', 'luxury-bags', 'designer-bags', 'crossbody-bags', 'totes', 'wallets-accessories']:
    data, ext, err = execute_shopify_graphql(query, {'handle': h})
    if data and data.get('collectionByHandle'):
        c = data['collectionByHandle']
        print(f"{h:22} | Count: {c['productsCount']['count']:4} | Rules: {c['ruleSet']}")
    else:
        print(f"{h:22} | Not found or error: {err}")
