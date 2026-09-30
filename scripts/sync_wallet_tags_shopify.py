"""
Sync & Partition Wallet Catalog on Shopify Admin GraphQL (ADR 0020, 2026 Edition)
- Identifies all wallet, card case, billfold, wristlet, and small leather goods products.
- Cleanses 'Designer Bags' and 'Luxury Bags' tags from them so they do NOT pollute bag collections.
- Assigns 'Wallets & Small Leather Goods', 'Wallets', 'Wallets & Accessories', and granular subcategory tags.
- Sets productType to 'Wallets & Small Leather Goods'.
"""
import os
import sys
import time
import json
from typing import Dict, Any, List, Set

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_taxonomy import resolve_gender, is_wallet_product

PRODUCT_UPDATE_MUTATION = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
      productType
      tags
    }
    userErrors {
      field
      message
    }
  }
}
"""

BAG_TAGS_TO_REMOVE = {
    "designer bags", "luxury bags", "handbags", "tote bags",
    "crossbody bags", "top handle bags", "clutches", "evening bags",
    "backpacks", "satchels", "bags", "bag"
}

def fetch_all_products() -> List[Dict[str, Any]]:
    query = """
    query getAllProducts($cursor: String) {
      products(first: 250, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          title
          vendor
          productType
          tags
        }
      }
    }
    """
    products = []
    cursor = None
    print("Fetching all products from Shopify catalog...")
    while True:
        data, _, err = execute_shopify_graphql(query, {"cursor": cursor})
        if err or not data:
            print(f"Error fetching products: {err}")
            break
        p_data = data.get("products", {})
        nodes = p_data.get("nodes", [])
        products.extend(nodes)
        print(f"  Fetched {len(products)} products so far...")
        if not p_data.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = p_data["pageInfo"]["endCursor"]
    return products

def sync_wallet_tags():
    all_prods = fetch_all_products()
    print(f"\nTotal store catalog: {len(all_prods)} products")

    wallets_to_update = []
    for p in all_prods:
        pid = p["id"]
        title = p.get("title") or ""
        pt = p.get("productType") or ""
        tags = p.get("tags") or []
        vendor = p.get("vendor") or ""

        # Check if product is a wallet / small leather good
        is_w = is_wallet_product({"title": title, "product_type": pt, "tags": tags})
        if not is_w:
            # Also check if existing tags or pt marked it as wallet
            if pt.lower() in ("wallets & small leather goods", "wallets", "small leather goods"):
                is_w = True
            elif any("wallet" in t.lower() or "card case" in t.lower() for t in tags):
                is_w = True

        if not is_w:
            continue

        # Build clean tags
        curr_tags_set = set(tags)
        cleaned_tags = [t for t in tags if t.lower() not in BAG_TAGS_TO_REMOVE]

        # Determine gender
        gender = resolve_gender({"title": title, "specifications": {}, "source_url": ""})
        # If product already had Men/Women tags, respect them
        has_men_tag = any(t in ("Men", "Men's", "Gender:Men") for t in tags)
        has_women_tag = any(t in ("Women", "Women's", "Gender:Women") for t in tags)
        if has_men_tag and not has_women_tag:
            gender = "Men"
        elif has_women_tag and not has_men_tag:
            gender = "Women"

        wallet_base_tags = [
            "Wallets & Small Leather Goods",
            "Wallets",
            "Wallets & Accessories",
            "Accessories",
            "Small Leather Goods"
        ]
        subcat_tags = []
        text = f"{pt} {title}".lower()
        if any(w in text for w in ["card case", "cardcase", "cardholder", "card holder", "passcase"]):
            subcat_tags.extend(["Card Cases", "Cardholders"])
        if any(w in text for w in ["wristlet"]):
            subcat_tags.append("Wristlets")
        if any(w in text for w in ["billfold"]):
            subcat_tags.append("Billfolds")
        if any(w in text for w in ["magsafe", "tech"]):
            subcat_tags.append("Tech Accessories")
        if any(w in text for w in ["passport"]):
            subcat_tags.append("Passport Cases")

        # Gender tags
        gender_tags = []
        if gender == "Men":
            cleaned_tags = [t for t in cleaned_tags if t.lower() not in ("women", "women's", "gender:women", "ladies")]
            gender_tags = ["Men", "Men's", "Gender:Men", "Gender:Men's"]
        elif gender == "Women":
            cleaned_tags = [t for t in cleaned_tags if t.lower() not in ("men", "men's", "gender:men")]
            gender_tags = ["Women", "Women's", "Gender:Women", "Gender:Women's", "Ladies"]

        new_tags = sorted(list(set(cleaned_tags + wallet_base_tags + subcat_tags + gender_tags)))
        target_pt = "Wallets & Small Leather Goods"

        tags_changed = (set(new_tags) != curr_tags_set)
        pt_changed = (pt != target_pt)

        if tags_changed or pt_changed:
            wallets_to_update.append({
                "id": pid,
                "title": title,
                "vendor": vendor,
                "old_pt": pt,
                "target_pt": target_pt,
                "old_tags": tags,
                "new_tags": new_tags
            })

    print(f"\nFound {len(wallets_to_update)} wallet products requiring tag/type synchronization.")
    
    updated_count = 0
    failed_count = 0

    for i, item in enumerate(wallets_to_update, 1):
        pid = item["id"]
        title = item["title"]
        target_pt = item["target_pt"]
        new_tags = item["new_tags"]

        input_payload = {
            "id": pid,
            "productType": target_pt,
            "tags": new_tags
        }

        data, ext, err = execute_shopify_graphql(PRODUCT_UPDATE_MUTATION, {"input": input_payload})
        if err or not data:
            print(f"[{i}/{len(wallets_to_update)}] FAILED {pid} '{title}': {err}")
            failed_count += 1
            continue

        res = data.get("productUpdate", {})
        u_errs = res.get("userErrors", [])
        if u_errs:
            print(f"[{i}/{len(wallets_to_update)}] UserErrors on {pid} '{title}': {u_errs}")
            failed_count += 1
        else:
            updated_count += 1
            if i % 10 == 0 or i == len(wallets_to_update):
                print(f"[{i}/{len(wallets_to_update)}] Updated: {item['vendor']} | {title[:40]}... (pt={target_pt})")

        # Brief rate limit sleep
        time.sleep(0.08)

    print("\n" + "=" * 80)
    print(f"WALLET SYNCHRONIZATION COMPLETE")
    print(f"Successfully updated: {updated_count}")
    print(f"Failed: {failed_count}")
    print("=" * 80)

if __name__ == "__main__":
    sync_wallet_tags()
