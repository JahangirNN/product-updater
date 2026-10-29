import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

# First list publications (sales channels)
query_pubs = """
{
  publications(first: 10) {
    nodes {
      id
      name
    }
  }
}
"""
res, _, _ = execute_shopify_graphql(query_pubs)
print("Publications:", res)
