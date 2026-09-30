import sys
import os
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

TAGS_ADD_MUTATION = """
mutation tagsAdd($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) {
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

METAFIELDS_SET_MUTATION = """
mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
      namespace
      key
      value
    }
    userErrors {
      field
      message
    }
  }
}
"""

PRODUCT_UPDATE_MUTATION = """
mutation updateProduct($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      vendor
      tags
    }
    userErrors {
      field
      message
    }
  }
}
"""

KNOWN_MK_MYSTORE_HANDLES = [
    "cooper-logo-billfold-wallet-with-passcase",
    "cooper-signature-billfold-wallet",
    "michael-kors-logo-print-wallet-belt-gift-set",
    "jet-set-travel-small-signature-logo-and-smooth-wristlet",
    "jet-set-travel-small-signature-logo-and-smooth-wristlet-1",
    "jet-set-travel-striped-signature-logo-convertible-wristlet",
]

def sync_michael_kors_ready_to_ship():
    print("=" * 80, flush=True)
    print("SYNCING MICHAEL KORS READY TO SHIP BADGES & TAGS ON SHOPIFY", flush=True)
    print("=" * 80, flush=True)

    all_products = []

    # 1. Fetch vendor:'Michael Kors' and vendor:'MICHAEL Michael Kors' products
    query = """
    query getMKProducts($cursor: String) {
      products(first: 50, after: $cursor, query: "vendor:'Michael Kors' OR vendor:'MICHAEL Michael Kors'") {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          title
          handle
          vendor
          tags
          status
        }
      }
    }
    """

    cursor = None
    page = 1
    while True:
        print(f"Fetching MK products page {page}...", flush=True)
        data, _, err = execute_shopify_graphql(query, variables={"cursor": cursor}, allow_retry=False)
        if err or not data:
            print("Error querying products:", err, flush=True)
            break
        p_data = data.get("products", {})
        nodes = p_data.get("nodes", [])
        all_products.extend(nodes)
        print(f"  Got {len(nodes)} products (total: {len(all_products)})", flush=True)
        if p_data.get("pageInfo", {}).get("hasNextPage"):
            cursor = p_data.get("pageInfo", {}).get("endCursor")
            page += 1
        else:
            break

    # 2. Also fetch the known "My Store" Michael Kors items
    print("Checking known My Store MK items...", flush=True)
    for handle in KNOWN_MK_MYSTORE_HANDLES:
        q_h = """
        query getByHandle($handle: String!) {
          productByHandle(handle: $handle) {
            id
            title
            handle
            vendor
            tags
            status
          }
        }
        """
        data_h, _, _ = execute_shopify_graphql(q_h, variables={"handle": handle}, allow_retry=False)
        p = data_h.get("productByHandle") if data_h else None
        if p and p["id"] not in [x["id"] for x in all_products]:
            all_products.append(p)
            print(f"  Added My Store item: {p['title']}", flush=True)

    print(f"\nTotal MK products to process: {len(all_products)}", flush=True)

    updated_count = 0
    metafield_count = 0
    vendor_fix_count = 0

    for idx, p in enumerate(all_products, 1):
        pid = p["id"]
        title = p["title"]
        vendor = p["vendor"]
        tags = set(p.get("tags") or [])
        status = p.get("status")

        # Fix vendor if it's "My Store"
        if vendor == "My Store":
            target_vendor = "MICHAEL Michael Kors" if any(w in title for w in ["Jet Set", "Cooper"]) else "Michael Kors"
            v_input = {"id": pid, "vendor": target_vendor}
            v_data, _, v_err = execute_shopify_graphql(PRODUCT_UPDATE_MUTATION, variables={"input": v_input}, allow_retry=False)
            if v_data and not v_err:
                vendor_fix_count += 1
                print(f"[{idx}/{len(all_products)}] Fixed vendor for '{title}' -> {target_vendor}", flush=True)

        # Ensure Ready to Ship & instant-ship tags
        needed_tags = []
        if "Ready to Ship" not in tags:
            needed_tags.append("Ready to Ship")
        if "instant-ship" not in tags:
            needed_tags.append("instant-ship")

        if needed_tags:
            t_data, _, t_err = execute_shopify_graphql(TAGS_ADD_MUTATION, variables={"id": pid, "tags": needed_tags}, allow_retry=False)
            if t_data and not t_err:
                updated_count += 1
                print(f"[{idx}/{len(all_products)}] Added tags {needed_tags} to '{title[:35]}'", flush=True)
            else:
                print(f"[{idx}/{len(all_products)}] Failed adding tags: {t_err}", flush=True)

        # Ensure custom.badges metafield
        mf_payload = [
            {
                "ownerId": pid,
                "namespace": "custom",
                "key": "badges",
                "type": "list.single_line_text_field",
                "value": json.dumps(["Ready to Ship"])
            }
        ]
        m_data, _, m_err = execute_shopify_graphql(METAFIELDS_SET_MUTATION, variables={"metafields": mf_payload}, allow_retry=False)
        if m_data and not m_err:
            metafield_count += 1

        time.sleep(0.05)

    print("=" * 80, flush=True)
    print("SYNC COMPLETE:", flush=True)
    print(f"  - Vendors fixed: {vendor_fix_count}", flush=True)
    print(f"  - Tags updated: {updated_count}", flush=True)
    print(f"  - Metafields set: {metafield_count}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    sync_michael_kors_ready_to_ship()
