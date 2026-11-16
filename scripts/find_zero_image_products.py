import os
import sys
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

PAGE_SIZE = 250

PRODUCTS_QUERY = """
query getProductsWithMedia($cursor: String) {
  products(first: 250, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      title
      handle
      status
      vendor
      productType
      totalInventory
      featuredImage {
        id
        url
      }
      media(first: 1) {
        nodes {
          id
        }
      }
    }
  }
}
"""

def scan_shopify_products():
    print("=" * 80)
    print("SCANNING ALL SHOPIFY PRODUCTS FOR ZERO-IMAGE ITEMS")
    print("=" * 80)

    has_next_page = True
    cursor = None
    total_scanned = 0
    zero_image_products = []

    while has_next_page:
        data, resp, err = execute_shopify_graphql(PRODUCTS_QUERY, variables={"cursor": cursor})
        if err:
            print(f"Error fetching products: {err}")
            time.sleep(2)
            continue

        products_data = data.get("products", {})
        nodes = products_data.get("nodes", [])
        page_info = products_data.get("pageInfo", {})

        for p in nodes:
            total_scanned += 1
            has_media = False
            if p.get("featuredImage") and p["featuredImage"].get("url"):
                has_media = True
            elif p.get("media", {}).get("nodes") and len(p["media"]["nodes"]) > 0:
                has_media = True

            if not has_media:
                zero_image_products.append({
                    "id": p["id"],
                    "title": p["title"],
                    "handle": p["handle"],
                    "status": p["status"],
                    "vendor": p["vendor"],
                    "productType": p["productType"],
                    "inventory": p.get("totalInventory", 0),
                    "admin_url": f"https://admin.shopify.com/store/c6f505-87/products/{p['id'].split('/')[-1]}",
                    "storefront_url": f"https://therareavenue.com/products/{p['handle']}"
                })

        print(f"Scanned {total_scanned} products... (Found {len(zero_image_products)} with 0 images so far)")

        has_next_page = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")

    print("\n" + "=" * 80)
    print(f"SCAN COMPLETED: Scanned {total_scanned} total products in Shopify.")
    print(f"TOTAL PRODUCTS WITH 0 IMAGES: {len(zero_image_products)}")
    print("=" * 80)

    # Save to JSON artifact
    output_path = os.path.join(PROJECT_ROOT, "storage", "zero_image_products.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_scanned": total_scanned,
            "zero_image_count": len(zero_image_products),
            "products": zero_image_products
        }, f, indent=2)
    print(f"Saved results to: {output_path}")

    # Also print breakdown by vendor & status
    if zero_image_products:
        vendor_counts = {}
        status_counts = {}
        for p in zero_image_products:
            v = p["vendor"] or "Unknown"
            s = p["status"] or "Unknown"
            vendor_counts[v] = vendor_counts.get(v, 0) + 1
            status_counts[s] = status_counts.get(s, 0) + 1

        print("\nBreakdown by Status:")
        for s, c in status_counts.items():
            print(f"  - {s}: {c}")

        print("\nBreakdown by Vendor:")
        for v, c in sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"  - {v}: {c}")

        print("\nSample Products with 0 Images (first 25):")
        for i, p in enumerate(zero_image_products[:25], 1):
            print(f"{i:>2}. [{p['status']}] {p['vendor']} - {p['title']}")
            print(f"    Handle: {p['handle']} | Inventory: {p['inventory']}")
            print(f"    Admin: {p['admin_url']}")

    return zero_image_products

if __name__ == "__main__":
    scan_shopify_products()
