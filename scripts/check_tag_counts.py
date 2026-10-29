import os, sys, json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getProductsByTag($query: String!) {
  products(first: 5, query: $query) {
    totalCount
    nodes {
      id
      title
      tags
    }
  }
}
"""

for tag_query in ["tag:Women", "tag:Women's", "tag:Gender:Women", "tag:Men", "tag:Men's", "tag:Gender:Men"]:
    data, ext, err = execute_shopify_graphql(query, {"query": tag_query})
    count = data.get("products", {}).get("totalCount") if data else "N/A"
    print(f"Query '{tag_query}' -> Count: {count}")
