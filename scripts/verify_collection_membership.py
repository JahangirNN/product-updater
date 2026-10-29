import os
import sys
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_auth import execute_shopify_graphql

EVIDENCE_FILE = os.path.join(PROJECT_ROOT, ".agents", "worker_mk_eyewear", "r2_provisioning_evidence.json")
PRODUCTS_DIR = os.path.join(PROJECT_ROOT, "storage", "db", "michaelkors", "products")

GET_COLLECTION_QUERY = """
query getCollectionEyewear($handle: String!, $cursor: String) {
  collectionByHandle(handle: $handle) {
    id
    title
    handle
    productsCount {
      count
    }
    products(first: 100, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        title
        handle
        status
        productType
      }
    }
  }
}
"""

def verify():
    # Read stamped products from disk
    files = sorted([f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json")])
    sunglasses_on_disk = []
    for f in files:
        with open(os.path.join(PRODUCTS_DIR, f), "r", encoding="utf-8") as jf:
            d = json.load(jf)
        if d.get("product_type") == "Sunglasses":
            sunglasses_on_disk.append(d)

    print(f"Total sunglasses on disk: {len(sunglasses_on_disk)}")
    disk_gids = set(p.get("shopify_product_id") for p in sunglasses_on_disk)
    assert None not in disk_gids, "Some sunglasses missing shopify_product_id on disk!"
    print(f"All {len(disk_gids)} sunglasses have stamped shopify_product_id.")

    # Query collection
    collection_products = []
    cursor = None
    collection_info = None

    while True:
        c_data, c_ext, c_err = execute_shopify_graphql(
            GET_COLLECTION_QUERY,
            variables={"handle": "designer-eyewear", "cursor": cursor}
        )
        if c_err or not c_data:
            print(f"Error querying collection: {c_err}")
            break

        c_node = c_data.get("collectionByHandle")
        if not c_node:
            print("Collection not found")
            break

        collection_info = {
            "id": c_node.get("id"),
            "title": c_node.get("title"),
            "handle": c_node.get("handle"),
            "count": c_node.get("productsCount", {}).get("count")
        }

        nodes = c_node.get("products", {}).get("nodes", [])
        collection_products.extend(nodes)

        page_info = c_node.get("products", {}).get("pageInfo", {})
        if page_info.get("hasNextPage") and page_info.get("endCursor"):
            cursor = page_info["endCursor"]
        else:
            break

    col_gids = set(p["id"] for p in collection_products)
    print(f"Collection: '{collection_info.get('title')}' ({collection_info.get('handle')})")
    print(f"Products in collection: {len(collection_products)}")
    print(f"Matched with local catalog: {len(disk_gids & col_gids)} / {len(disk_gids)}")

    missing = disk_gids - col_gids
    if missing:
        print(f"Still pending index for {len(missing)} items: {missing}")
    else:
        print(f"PERFECT MATCH: All {len(disk_gids)} Michael Kors sunglasses are cleanly populated in /collections/designer-eyewear!")

    # Update evidence file
    if os.path.exists(EVIDENCE_FILE):
        with open(EVIDENCE_FILE, "r", encoding="utf-8") as ef:
            ev = json.load(ef)
        ev["smart_collection"] = {
            "title": collection_info.get("title"),
            "handle": collection_info.get("handle"),
            "id": collection_info.get("id"),
            "products_count": len(collection_products),
            "all_46_present": len(missing) == 0
        }
        ev["status"] = "PASS" if len(missing) == 0 and ev.get("total_sunglasses_provisioned") == 46 else ev.get("status")
        with open(EVIDENCE_FILE, "w", encoding="utf-8") as ef:
            json.dump(ev, ef, indent=2)
        print(f"Updated evidence in {EVIDENCE_FILE}")

if __name__ == "__main__":
    verify()
