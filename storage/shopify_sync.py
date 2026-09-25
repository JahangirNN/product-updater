"""
Shopify Catalog Ingestion & Real-Time Delta Synchronization Bridge
Pure functions for upserting products and pushing live price/stock delta shifts to Shopify Admin GraphQL.
Adheres to ADR 0005, 0006, 0015, 0019, 0020, and 0021.
"""
import os
import sys
import json
import time
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_taxonomy import prepare_product_set_payload
from storage.forex import get_usd_to_inr_rate
from storage.logger import log_info, log_success, log_warning, log_error

PRODUCT_SET_MUTATION = """
mutation productSet($input: ProductSetInput!, $synchronous: Boolean!) {
  productSet(input: $input, synchronous: $synchronous) {
    product {
      id
      title
      handle
      status
      totalVariants
      onlineStoreUrl
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""


def upsert_product_to_shopify(prod: Dict[str, Any], forex_rate: Optional[float] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Upsert a product to Shopify using the productSet GraphQL mutation.
    Transforms product into schema-compliant ProductSetInput using shopify_taxonomy.
    Returns (success, product_node, error_message).
    """
    if forex_rate is None:
        forex_rate = get_usd_to_inr_rate()
        
    payload = prepare_product_set_payload(prod, forex_rate)
    
    data, ext, err = execute_shopify_graphql(
        PRODUCT_SET_MUTATION,
        variables={"input": payload, "synchronous": True}
    )
    
    if err or not data:
        return False, None, f"GraphQL Error: {err}"
        
    res = data.get("productSet", {})
    u_errors = res.get("userErrors", [])
    if u_errors:
        err_details = "; ".join(f"{e.get('field')}: {e.get('message')}" for e in u_errors)
        return False, None, f"UserErrors: {err_details}"
        
    p_node = res.get("product")
    return True, p_node, ""


def sync_delta_to_shopify(updated_product: Dict[str, Any], delta_res: Dict[str, Any], forex_rate: Optional[float] = None) -> bool:
    """
    Instantly push price or stock shifts to Shopify for an already-linked product.
    Returns True if successfully synchronized.
    """
    shopify_id = updated_product.get("shopify_product_id")
    if not shopify_id:
        return False
        
    if forex_rate is None:
        forex_rate = get_usd_to_inr_rate()
        
    success, p_node, err = upsert_product_to_shopify(updated_product, forex_rate)
    if success:
        log_success(f"[SHOPIFY SYNC] Synced delta for {updated_product.get('title', '')[:35]} (GID: {shopify_id})")
        return True
    else:
        log_error(f"[SHOPIFY SYNC FAIL] Failed to sync delta for {updated_product.get('title', '')[:35]}: {err}")
        return False


def drain_delta_events_queue(limit: int = 100, forex_rate: Optional[float] = None) -> Dict[str, Any]:
    """
    Process queued delta events from storage/db/history/delta_events.jsonl where shopify_sync_pending is True.
    Upserts products to Shopify and marks shopify_sync_pending = False.
    """
    events_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db", "history", "delta_events.jsonl")
    if not os.path.exists(events_path):
        return {"processed": 0, "success": 0, "failed": 0}

    if forex_rate is None:
        forex_rate = get_usd_to_inr_rate()

    try:
        with open(events_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        log_error(f"Failed to read delta events queue: {e}")
        return {"processed": 0, "success": 0, "failed": 0}

    events = []
    for line in lines:
        if line.strip():
            try:
                events.append(json.loads(line.strip()))
            except Exception:
                pass

    processed = 0
    success_count = 0
    fail_count = 0
    updated = False

    for evt in events:
        if processed >= limit:
            break
        if evt.get("shopify_sync_pending"):
            processed += 1
            store = evt.get("store")
            p_id = evt.get("product_id")
            if not store or not p_id:
                continue

            p_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db", store, "products", f"{p_id}.json")
            if not os.path.exists(p_path):
                continue

            try:
                with open(p_path, "r", encoding="utf-8") as pf:
                    prod = json.load(pf)

                ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)
                if ok and p_node:
                    evt["shopify_sync_pending"] = False
                    evt["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    
                    if not prod.get("shopify_product_id") and p_node.get("id"):
                        prod["shopify_product_id"] = p_node.get("id")
                        prod["shopify_handle"] = p_node.get("handle")
                        prod["shopify_synced_at"] = evt["shopify_synced_at"]
                        with open(p_path, "w", encoding="utf-8") as pf:
                            json.dump(prod, pf, indent=2, ensure_ascii=False)
                            
                    success_count += 1
                    updated = True
                else:
                    fail_count += 1
                    log_warning(f"[QUEUE DRAIN FAIL] {p_id}: {err}")
            except Exception as e:
                fail_count += 1
                log_error(f"[QUEUE DRAIN ERROR] {p_id}: {e}")

    if updated:
        tmp_path = f"{events_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt, ensure_ascii=False) + "\n")
        os.replace(tmp_path, events_path)

    return {"processed": processed, "success": success_count, "failed": fail_count}
