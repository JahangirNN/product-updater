import os
import sys
import json
import httpx

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from stores.coach.delta import check_price_and_stock as check_coach
from stores.jwpei.delta import check_price_and_stock as check_jwpei
from stores.michaelkors.delta import check_price_and_stock as check_mk

def test_store_delta(store_name, delta_fn):
    pdir = os.path.join(PROJECT_ROOT, "storage", "db", store_name, "products")
    files = [f for f in os.listdir(pdir) if f.endswith(".json")]
    assert len(files) > 0, f"No products found in {pdir}"
    
    with open(os.path.join(pdir, files[0]), "r", encoding="utf-8") as f:
        prod = json.load(f)
        
    print(f"\nTesting live delta for {store_name.upper()}...")
    print(f"Title: {prod.get('title')}")
    print(f"URL: {prod.get('source_url')}")
    
    with httpx.Client(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
        res = delta_fn(prod, client=client)
        print(f"Delta Result status: {res.get('status')}")
        print(f"Price: {res.get('current_source_price')} (old: {res.get('old_source_price')})")
        print(f"Availability: {res.get('availability')}")
        return res

if __name__ == "__main__":
    res_jw = test_store_delta("jwpei", check_jwpei)
    res_coach = test_store_delta("coach", check_coach)
    res_mk = test_store_delta("michaelkors", check_mk)
    print("\nALL 3 STORE DELTA CHECKS COMPLETED.")
