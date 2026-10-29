"""
Provisioning script for Michael Kors Designer Eyewear (Requirement R2)
Provisions all 46 sunglasses to Shopify Admin GraphQL using productSet and productCreateMedia,
stamps disk JSON files with shopify_product_id, shopify_handle, shopify_synced_at,
rebuilds master index, and verifies clean population of /collections/designer-eyewear.
"""
import os
import sys
import json
import time
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.db import build_and_save_index
from storage.logger import log_info, log_success, log_warning, log_error

PRODUCTS_DIR = os.path.join(PROJECT_ROOT, "storage", "db", "michaelkors", "products")
EVIDENCE_FILE = os.path.join(PROJECT_ROOT, ".agents", "worker_mk_eyewear", "r2_provisioning_evidence.json")

PRODUCT_CREATE_MEDIA_MUTATION = """
mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
  productCreateMedia(media: $media, productId: $productId) {
    media {
      id
      status
      mediaContentType
    }
    mediaUserErrors {
      field
      message
    }
  }
}
"""

GET_PRODUCT_DETAILS_QUERY = """
query getProductDetails($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    productType
    tags
    totalVariants
    media(first: 10) {
      nodes {
        id
        status
        mediaContentType
        ... on MediaImage {
          image {
            url
          }
        }
      }
    }
    variants(first: 5) {
      nodes {
        id
        sku
        price
      }
    }
    collections(first: 10) {
      nodes {
        id
        title
        handle
      }
    }
  }
}
"""

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
        variants(first: 1) {
          nodes {
            id
            price
            sku
          }
        }
        featuredImage {
          url
        }
      }
    }
  }
}
"""

def provision_media_if_needed(product_id: str, image_urls: List[str], existing_media_count: int) -> List[Dict[str, Any]]:
    if existing_media_count >= len(image_urls) or not image_urls:
        return []
    
    missing_urls = image_urls[existing_media_count:]
    media_inputs = [{"originalSource": u, "mediaContentType": "IMAGE"} for u in missing_urls]
    
    data, ext, err = execute_shopify_graphql(
        PRODUCT_CREATE_MEDIA_MUTATION,
        variables={"productId": product_id, "media": media_inputs}
    )
    if err or not data:
        log_error(f"productCreateMedia failed for {product_id}: {err}")
        return []
        
    res = data.get("productCreateMedia", {})
    return res.get("media", [])

def provision_all_eyewear():
    files = sorted([f for f in os.listdir(PRODUCTS_DIR) if f.endswith(".json")])
    sunglasses = []
    for f in files:
        fpath = os.path.join(PRODUCTS_DIR, f)
        with open(fpath, "r", encoding="utf-8") as jf:
            d = json.load(jf)
        if d.get("product_type") == "Sunglasses":
            sunglasses.append((f, fpath, d))

    print(f"Loaded {len(sunglasses)} sunglasses candidate files.")
    forex_rate = get_usd_to_inr_rate()
    print(f"Using live forex rate: 1 USD = INR {forex_rate:.2f}")

    provisioned_results = []
    failed_items = []

    for idx, (fname, fpath, prod) in enumerate(sunglasses, 1):
        p_id = prod.get("id")
        title = prod.get("title")
        images = prod.get("images") or []
        print(f"[{idx}/{len(sunglasses)}] Provisioning '{title}' ({prod.get('source_sku')})...", end=" ", flush=True)

        ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)
        if not ok or not p_node:
            print(f"FAILED -> {err}")
            failed_items.append({"file": fname, "title": title, "error": err})
            continue

        shop_id = p_node.get("id")
        shop_handle = p_node.get("handle")
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Verify product details via query
        p_data, p_ext, p_err = execute_shopify_graphql(GET_PRODUCT_DETAILS_QUERY, variables={"id": shop_id})
        shopify_product = (p_data or {}).get("product", {})
        media_nodes = shopify_product.get("media", {}).get("nodes", [])

        # If media nodes is 0 or less than images, trigger productCreateMedia
        if len(media_nodes) < len(images):
            created_media = provision_media_if_needed(shop_id, images, len(media_nodes))
            if created_media:
                # Re-fetch
                p_data, p_ext, p_err = execute_shopify_graphql(GET_PRODUCT_DETAILS_QUERY, variables={"id": shop_id})
                shopify_product = (p_data or {}).get("product", {})
                media_nodes = shopify_product.get("media", {}).get("nodes", [])

        # Stamp disk file
        prod["shopify_product_id"] = shop_id
        prod["shopify_handle"] = shop_handle
        prod["shopify_synced_at"] = now_iso
        prod["shopify_sync_pending"] = False

        with open(fpath, "w", encoding="utf-8") as jf:
            json.dump(prod, jf, indent=2, ensure_ascii=False)

        variant_nodes = shopify_product.get("variants", {}).get("nodes", [])
        var_id = variant_nodes[0].get("id") if variant_nodes else None
        var_price = variant_nodes[0].get("price") if variant_nodes else None

        collections_assigned = [c.get("handle") for c in shopify_product.get("collections", {}).get("nodes", [])]

        print(f"SUCCESS -> GID: {shop_id} | Handle: {shop_handle} | Media: {len(media_nodes)} | Price: INR {var_price}")
        provisioned_results.append({
            "file": fname,
            "id": p_id,
            "title": title,
            "source_sku": prod.get("source_sku"),
            "shopify_product_id": shop_id,
            "shopify_handle": shop_handle,
            "shopify_synced_at": now_iso,
            "variant_id": var_id,
            "variant_price_inr": var_price,
            "media_count": len(media_nodes),
            "media_urls": [m.get("image", {}).get("url") for m in media_nodes if m.get("image")],
            "tags": shopify_product.get("tags", []),
            "collections": collections_assigned
        })

        time.sleep(0.35)

    print("=" * 80)
    print(f"PROVISIONING COMPLETE: {len(provisioned_results)} succeeded, {len(failed_items)} failed.")
    print("=" * 80)

    # Rebuild central master index
    print("Rebuilding central master index (storage/db/index.json)...")
    build_and_save_index()
    print("Master index successfully updated.")

    # Verification: Query /collections/designer-eyewear
    print("Verifying membership in /collections/designer-eyewear...")
    time.sleep(3)  # allow Shopify background smart collection rule evaluation to index

    collection_products = []
    cursor = None
    collection_info = None

    while True:
        c_data, c_ext, c_err = execute_shopify_graphql(
            GET_COLLECTION_QUERY,
            variables={"handle": "designer-eyewear", "cursor": cursor}
        )
        if c_err or not c_data:
            log_error(f"Failed to fetch collection: {c_err}")
            break

        c_node = c_data.get("collectionByHandle")
        if not c_node:
            log_error("Collection 'designer-eyewear' not found!")
            break

        collection_info = {
            "id": c_node.get("id"),
            "title": c_node.get("title"),
            "handle": c_node.get("handle"),
            "total_count": c_node.get("productsCount", {}).get("count")
        }

        nodes = c_node.get("products", {}).get("nodes", [])
        collection_products.extend(nodes)

        page_info = c_node.get("products", {}).get("pageInfo", {})
        if page_info.get("hasNextPage") and page_info.get("endCursor"):
            cursor = page_info["endCursor"]
        else:
            break

    print(f"Collection: '{collection_info.get('title')}' (Handle: {collection_info.get('handle')}, GID: {collection_info.get('id')})")
    print(f"Products populated in collection: {len(collection_products)}")

    # Check that all 46 products are present
    provisioned_gids = set(p["shopify_product_id"] for p in provisioned_results)
    collection_gids = set(p["id"] for p in collection_products)
    missing_gids = provisioned_gids - collection_gids

    print(f"Matched GIDs: {len(provisioned_gids & collection_gids)} / {len(provisioned_gids)}")
    if missing_gids:
        print(f"Warning: {len(missing_gids)} GIDs not yet visible in collection query: {missing_gids}")

    # Build evidence dictionary
    evidence = {
        "status": "PASS" if len(provisioned_results) == 46 and len(failed_items) == 0 else "PARTIAL",
        "target_store": "hewmvw-am.myshopify.com",
        "total_sunglasses_provisioned": len(provisioned_results),
        "total_failed": len(failed_items),
        "smart_collection": {
            "title": collection_info.get("title") if collection_info else "Designer Sunglasses & Eyewear",
            "handle": collection_info.get("handle") if collection_info else "designer-eyewear",
            "id": collection_info.get("id") if collection_info else None,
            "products_count": len(collection_products),
            "all_46_present": len(missing_gids) == 0
        },
        "provisioned_products": provisioned_results,
        "failed_items": failed_items
    }

    with open(EVIDENCE_FILE, "w", encoding="utf-8") as ef:
        json.dump(evidence, ef, indent=2)

    print(f"Evidence saved to: {EVIDENCE_FILE}")

if __name__ == "__main__":
    provision_all_eyewear()
