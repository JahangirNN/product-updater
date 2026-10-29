"""
Audit and heal any remaining JW PEI products whose featuredMedia on Shopify
does not match their authentic colorway / primary image.
"""
import os
import sys
import json
import glob
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.shopify_taxonomy import prepare_product_set_payload

QUERY = """
query getProductMedia($id: ID!) {
  product(id: $id) {
    id
    title
    featuredMedia {
      ... on MediaImage {
        image {
          url
        }
      }
    }
  }
}
"""

def audit_and_heal():
    files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products", "*.json"))
    print(f"Auditing {len(files)} JW PEI products on live Shopify...")
    forex_rate = get_usd_to_inr_rate()

    to_heal = []

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            prod = json.load(f)

        pid = prod.get("shopify_product_id")
        if not pid:
            continue

        payload = prepare_product_set_payload(prod, forex_rate)
        expected_f0 = payload.get("files", [{}])[0].get("originalSource", "")
        if not expected_f0:
            continue

        data, ext, err = execute_shopify_graphql(QUERY, variables={"id": pid})
        if err or not data or not data.get("product"):
            to_heal.append((fpath, prod, "Fetch Error: " + err))
            continue

        live_fmedia = ((data["product"].get("featuredMedia") or {}).get("image") or {}).get("url", "")
        # Compare filename
        expected_name = expected_f0.split("?")[0].split("/")[-1].lower()
        live_name = live_fmedia.split("?")[0].split("/")[-1].lower()

        # strip shopify hash if present e.g. name_hash.jpg
        expected_base = expected_name.split(".")[0][:15]
        live_base = live_name.split(".")[0][:15]

        if expected_base != live_base:
            to_heal.append((fpath, prod, f"Mismatch: expected {expected_name[:25]} vs live {live_name[:25]}"))

    print(f"\nAudit complete: {len(to_heal)} products need re-sync / healing.")

    if not to_heal:
        print("ALL JW PEI PRODUCTS 100% IN SYNC WITH AUTHENTIC FEATURED MEDIA!")
        return

    print("Healing affected products with polite rate pacing...")
    healed = 0
    failed = 0
    for fpath, prod, reason in to_heal:
        print(f"Healing: {prod.get('title')[:45]} ({prod.get('shopify_product_id')}) - {reason}")
        ok, pnode, err = upsert_product_to_shopify(prod, forex_rate)
        if ok:
            healed += 1
            print(f"  -> SUCCESS ({healed}/{len(to_heal)})")
        else:
            failed += 1
            print(f"  -> FAILED: {err}")
        time.sleep(0.5)

    print("=" * 70)
    print(f"HEALING COMPLETE: {healed} healed, {failed} failed.")
    print("=" * 70)

if __name__ == "__main__":
    audit_and_heal()
