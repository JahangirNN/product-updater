"""
Batch Strip 'Ready to Ship' and 'instant-ship' tags from all products on Shopify.
Queries products with matching tags and removes them in rate-limited batches.
"""
import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_error

QUERY_PRODUCTS = """
query getTaggedProducts($cursor: String) {
  products(first: 50, query: "tag:'Ready to Ship' OR tag:instant-ship", after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      title
      tags
    }
  }
}
"""

MUTATION_TAGS_REMOVE = """
mutation tagsRemove($id: ID!, $tags: [String!]!) {
  tagsRemove(id: $id, tags: $tags) {
    node {
      id
    }
    userErrors {
      field
      message
    }
  }
}
"""

def run_batch_tag_cleanup():
    log_info("[TAG CLEANUP] Starting batch removal of 'Ready to Ship' & 'instant-ship' tags...")
    total_stripped = 0
    cursor = None
    
    while True:
        data, cost, err = execute_shopify_graphql(QUERY_PRODUCTS, variables={"cursor": cursor})
        if err or not data:
            log_error(f"[TAG CLEANUP] GraphQL error: {err}")
            time.sleep(3)
            continue
            
        prods = data.get("products", {})
        nodes = prods.get("nodes", [])
        if not nodes:
            log_info("[TAG CLEANUP] No more tagged products found!")
            break
            
        for node in nodes:
            pid = node["id"]
            _, _, m_err = execute_shopify_graphql(
                MUTATION_TAGS_REMOVE, 
                variables={"id": pid, "tags": ["Ready to Ship", "instant-ship"]}
            )
            if not m_err:
                total_stripped += 1
            if total_stripped % 50 == 0:
                log_info(f"[TAG CLEANUP] Successfully stripped tags from {total_stripped} products...")
                time.sleep(0.5)
                
        page_info = prods.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            log_info("[TAG CLEANUP] Reached last page of tagged products.")
            break
        cursor = page_info.get("endCursor")
        
    log_success(f"[TAG CLEANUP] Complete! Total products cleaned: {total_stripped}")

if __name__ == "__main__":
    run_batch_tag_cleanup()
