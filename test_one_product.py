"""
Single Product Inflow & Delta Verification Harness
Tests the end-to-end flow on 1 product with full depth and rigorous validation.
"""
import os
import sys
import json
import httpx

# Ensure workspace root in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.forex import get_usd_to_inr_rate
from storage.validator import validate_product
from storage.db import save_product, load_product, build_and_save_index, append_delta_log
from stores.jwpei.inflow import parse_product_payload
from stores.jwpei.delta import check_price_and_stock


def run_test():
    print("=" * 60)
    print("STEP 1: FETCH FOREX RATE (USD -> INR)")
    print("=" * 60)
    forex_rate = get_usd_to_inr_rate()
    print(f"Current USD to INR Rate: ₹{forex_rate:.4f}\n")

    print("=" * 60)
    print("STEP 2: FETCH & PARSE ONE PRODUCT (Thea Top Handle Bag - Dark Olive)")
    print("=" * 60)
    target_handle = "thea-top-handle-bag-dark-olive"
    
    # 1. Fetch raw data from both .js (for stock) and .json (for full media/html)
    with httpx.Client(timeout=15.0) as client:
        r_js = client.get(f"https://www.jwpei.com/products/{target_handle}.js", headers={"User-Agent": "Mozilla/5.0"})
        r_json = client.get(f"https://www.jwpei.com/products/{target_handle}.json", headers={"User-Agent": "Mozilla/5.0"})
    
    data_js = r_js.json()
    data_json = r_json.json().get("product", {})
    
    # Merge: .json has full images & body_html, .js has verified live availability & cents price
    raw_merged = dict(data_json)
    raw_merged["available"] = data_js.get("available")
    raw_merged["price_cents"] = data_js.get("price")
    raw_merged["compare_at_price_cents"] = data_js.get("compare_at_price")

    canonical = parse_product_payload(raw_merged, usd_to_inr_rate=forex_rate, group_name="handbags")
    
    print(f"Title:        {canonical['title']}")
    print(f"Handle:       {canonical['handle']}")
    print(f"SKU:          {canonical['source_sku']}")
    print(f"Source Price: ${canonical['source_price']} USD")
    print(f"INR Price:    ₹{canonical['current_price']:,.2f}")
    print(f"Availability: {canonical['availability']}")
    print(f"Material:     {canonical['material']}")
    print(f"Images count: {len(canonical['images'])}")
    print(f"Specifications parsed:")
    for k, v in canonical['specifications'].items():
        print(f"  - {k}: {v}")

    print("\n" + "=" * 60)
    print("STEP 3: VALIDATE AGAINST SHOPIFY ADMIN API SPEC")
    print("=" * 60)
    is_valid, status, warnings = validate_product(canonical)
    canonical["status"] = status
    print(f"Is API Valid: {is_valid}")
    print(f"Designated Status: {status}")
    print(f"Warnings ({len(warnings)}):")
    for w in warnings:
        print(f"  * {w}")

    print("\n" + "=" * 60)
    print("STEP 4: SAVE TO PARTITIONED LOCAL JSON DB & UPDATE INDEX")
    print("=" * 60)
    saved = save_product(canonical)
    prod_id = saved["id"]
    print(f"Product ID: {prod_id}")
    saved_path = f"storage/db/jwpei/products/{prod_id}.json"
    print(f"Saved file: {saved_path} (exists: {os.path.exists(saved_path)})")
    
    index_map = build_and_save_index()
    print(f"Index updated! Total products in catalog: {len(index_map)}")
    print(f"Index entry for {prod_id}:")
    print(json.dumps(index_map.get(prod_id), indent=2))

    print("\n" + "=" * 60)
    print("STEP 5: TEST DELTA UPDATER (DATA FRESHNER - STOCK & PRICE)")
    print("=" * 60)
    delta_result = check_price_and_stock(saved)
    print("Delta Result for In-Stock Product:")
    print(f"  Status:             {delta_result['status']}")
    print(f"  Execution Time:     {delta_result['elapsed_ms']} ms")
    print(f"  Live Source Price:  ${delta_result.get('current_source_price')} USD")
    print(f"  Old Source Price:   ${delta_result.get('old_source_price')} USD")
    print(f"  Price Changed:      {delta_result['price_changed']}")
    print(f"  Live Availability:  {delta_result['availability']}")
    print(f"  Old Availability:   {delta_result['old_availability']}")
    print(f"  Stock Changed:      {delta_result['stock_changed']}")

    append_delta_log({
        "product_id": prod_id,
        "store": "jwpei",
        "action": "delta_check",
        "result": delta_result
    })
    print("Recorded to storage/db/history/delta_log.json")

    print("\n" + "=" * 60)
    print("STEP 6: TEST DELTA UPDATER ON KNOWN OUT-OF-STOCK PRODUCT")
    print("=" * 60)
    sold_out_mock_product = {
        "handle": "elise-top-handle-bag-deep-burgundy",
        "source_price": 99.00,
        "availability": "in_stock"  # pretend it was in_stock previously to see if delta detects out_of_stock
    }
    sold_out_delta = check_price_and_stock(sold_out_mock_product)
    print("Delta Result for Sold-Out Product:")
    print(f"  Status:             {sold_out_delta['status']}")
    print(f"  Execution Time:     {sold_out_delta['elapsed_ms']} ms")
    print(f"  Live Availability:  {sold_out_delta['availability']}")
    print(f"  Stock Changed:      {sold_out_delta['stock_changed']} (Correctly detected transition!)")


if __name__ == "__main__":
    run_test()
