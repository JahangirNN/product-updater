"""
Migrate Catalog Color Taxonomy
Classifies all active products on Shopify into 12 standardized luxury color families
and attaches canonical tags (Color:Black, Color:Brown, etc.) via GraphQL tagsAdd mutation.
"""
import os
import sys
import time
import concurrent.futures
from typing import Dict, Any, List, Set


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_taxonomy import resolve_color_family, extract_variant_color


def get_products_page(cursor: str = None, page_size: int = 50) -> Dict[str, Any]:
    after_clause = f', after: "{cursor}"' if cursor else ""
    query = f"""
    {{
      products(first: {page_size}, query: "status:ACTIVE"{after_clause}) {{
        pageInfo {{
          hasNextPage
          endCursor
        }}
        nodes {{
          id
          title
          handle
          tags
          options {{
            name
            values
          }}
          variants(first: 20) {{
            nodes {{
              title
              selectedOptions {{
                name
                value
              }}
            }}
          }}
        }}
      }}
    }}
    """
    data, ext, err = execute_shopify_graphql(query)
    if err:
        print(f"Error fetching products: {err}")
        return {}
    return data.get("products", {})


def add_product_color_tags(product_id: str, new_tags: List[str]) -> bool:
    mutation = """
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
    data, ext, err = execute_shopify_graphql(mutation, variables={"id": product_id, "tags": new_tags})
    if err:
        print(f"Error adding tags to {product_id}: {err}")
        return False
    user_errors = data.get("tagsAdd", {}).get("userErrors", [])
    if user_errors:
        print(f"UserErrors for {product_id}: {user_errors}")
        return False
    return True


def run_migration(dry_run: bool = False, max_products: int = None):
    print("=" * 80)
    print(f"STARTING CATALOG COLOR TAXONOMY MIGRATION (DryRun={dry_run})")
    print("=" * 80)

    cursor = None
    total_processed = 0
    total_updated = 0
    start_time = time.time()

    while True:
        page = get_products_page(cursor=cursor, page_size=50)
        nodes = page.get("nodes", [])
        if not nodes:
            break

        items_to_update: List = []
        for p in nodes:
            pid = p["id"]
            title = p["title"]
            existing_tags = set(p.get("tags") or [])
            
            # Determine color families
            color_families: Set[str] = set()
            
            # 1. From options
            for opt in p.get("options", []):
                opt_name = (opt.get("name") or "").lower()
                if "color" in opt_name or "colour" in opt_name:
                    for val in opt.get("values", []):
                        for fam in resolve_color_family(val, title):
                            color_families.add(fam)
                            
            # 2. From variants
            for v in p.get("variants", {}).get("nodes", []):
                # check selectedOptions
                for so in v.get("selectedOptions", []):
                    so_name = (so.get("name") or "").lower()
                    if "color" in so_name or "colour" in so_name:
                        for fam in resolve_color_family(so.get("value", ""), title):
                            color_families.add(fam)
                # check title delimiter
                c = extract_variant_color(v)
                if c:
                    for fam in resolve_color_family(c, title):
                        color_families.add(fam)

            # 3. Fallback to product title
            if not color_families:
                for fam in resolve_color_family("", title):
                    color_families.add(fam)

            # Build canonical tags
            required_tags = [f"Color:{fam}" for fam in color_families]
            missing_tags = [t for t in required_tags if t not in existing_tags]

            total_processed += 1
            if missing_tags:
                items_to_update.append((pid, title, missing_tags))

        # Update batch concurrently
        if items_to_update:
            if not dry_run:
                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                    futures = {
                        executor.submit(add_product_color_tags, item[0], item[2]): item
                        for item in items_to_update
                    }
                    for fut in concurrent.futures.as_completed(futures):
                        item = futures[fut]
                        try:
                            ok = fut.result()
                            if ok:
                                total_updated += 1
                        except Exception as e:
                            print(f"Error updating {item[0]}: {e}")
            else:
                total_updated += len(items_to_update)

            print(f"Processed {total_processed} products | Updated {total_updated} with color tags...")

        if max_products and total_processed >= max_products:
            print(f"Reached limit of {max_products} products.")
            break

        page_info = page.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"MIGRATION COMPLETE in {elapsed:.1f}s")
    print(f"Total Processed: {total_processed}")
    print(f"Total Updated:   {total_updated}")
    print("=" * 80)


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])
    run_migration(dry_run=is_dry, max_products=limit)
