import os
import sys
import glob
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for store in ["jwpei", "coach", "michaelkors"]:
    files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", store, "products", "*.json"))
    total_prods = len(files)
    multi_vars = 0
    vars_with_img = 0
    vars_without_img = 0
    sample_prod = None

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
        except Exception:
            continue

        variants = d.get("variants") or []
        if len(variants) > 1:
            multi_vars += 1
            if not sample_prod:
                sample_prod = d
            for v in variants:
                if isinstance(v, dict):
                    v_img = v.get("image_url") or v.get("image") or (v.get("images") or [None])[0]
                    if v_img:
                        vars_with_img += 1
                    else:
                        vars_without_img += 1

    print(f"STORE: {store.upper()}")
    print(f"  Total products: {total_prods}")
    print(f"  Multi-variant products: {multi_vars}")
    print(f"  Variants with image: {vars_with_img}")
    print(f"  Variants without image: {vars_without_img}")
    if sample_prod:
        print(f"  Sample product: {sample_prod.get('handle')}")
        for v in sample_prod.get("variants", [])[:3]:
            print(f"    var title: {v.get('title')}, color: {v.get('color')}, img: {v.get('image_url') or v.get('image')}")
