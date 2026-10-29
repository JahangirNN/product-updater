"""
High-Performance Batch Strip of Ready to Ship Tags.
Collects all product IDs tagged with 'Ready to Ship', 'instant-ship', 'ready-to-ship', etc.
and removes the tags concurrently via Shopify Admin GraphQL tagsRemove.
"""
import os
import sys
import time
import concurrent.futures
from typing import List, Set

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_error

TAGS_TO_REMOVE = [
    "Ready to Ship",
    "instant-ship",
    "ready-to-ship",
    "Instant Ship",
    "manual-instant-ship-active"
]

QUERY_PRODUCTS = """
query getTaggedProducts($cursor: String) {
  products(first: 250, query: "tag:'Ready to Ship' OR tag:instant-ship OR tag:ready-to-ship OR tag:'Instant Ship'", after: $cursor) {
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


def collect_all_tagged_product_ids() -> List[str]:
    log_info("[TAG CLEANUP] Collecting all product IDs tagged with Ready to Ship...")
    product_ids: Set[str] = set()
    cursor = None

    while True:
        data, _, err = execute_shopify_graphql(QUERY_PRODUCTS, variables={"cursor": cursor})
        if err or not data:
            log_error(f"[TAG CLEANUP] Error fetching tagged products: {err}")
            time.sleep(2)
            continue

        products_data = data.get("products", {})
        nodes = products_data.get("nodes", [])
        if not nodes:
            break

        for node in nodes:
            product_ids.add(node["id"])

        page_info = products_data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    log_info(f"[TAG CLEANUP] Found {len(product_ids)} unique products to clean.")
    return list(product_ids)


def remove_tags_from_product(product_id: str) -> bool:
    try:
        data, _, err = execute_shopify_graphql(
            MUTATION_TAGS_REMOVE,
            variables={"id": product_id, "tags": TAGS_TO_REMOVE}
        )
        if err:
            return False
        res = data.get("tagsRemove", {})
        errs = res.get("userErrors", [])
        return len(errs) == 0
    except Exception:
        return False


def run_cleanup():
    start_time = time.time()
    product_ids = collect_all_tagged_product_ids()
    total_products = len(product_ids)

    if total_products == 0:
        log_success("[TAG CLEANUP] Zero products currently tagged with Ready to Ship. Clean!")
        return

    log_info(f"[TAG CLEANUP] Starting concurrent removal across {total_products} products (workers=10)...")
    cleaned_count = 0
    failed_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_pid = {executor.submit(remove_tags_from_product, pid): pid for pid in product_ids}
        for future in concurrent.futures.as_completed(future_to_pid):
            success = future.result()
            if success:
                cleaned_count += 1
            else:
                failed_count += 1

            if (cleaned_count + failed_count) % 100 == 0 or (cleaned_count + failed_count) == total_products:
                log_info(f"[TAG CLEANUP] Progress: {cleaned_count + failed_count}/{total_products} (Success: {cleaned_count}, Failed: {failed_count})")

    elapsed = time.time() - start_time
    log_success(f"[TAG CLEANUP] Completed in {elapsed:.1f}s! Successfully cleaned {cleaned_count}/{total_products} products.")


if __name__ == "__main__":
    run_cleanup()
