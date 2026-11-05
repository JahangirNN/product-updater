import json
import glob
import os

sephora_dir = "product-updater/storage/db/sephora/products"
files = glob.glob(os.path.join(sephora_dir, "*.json"))
print(f"Auditing and updating {len(files)} Sephora product JSONs...")

updated_count = 0
range_count = 0

for pf in files:
    with open(pf, "r", encoding="utf-8") as f:
        prod = json.load(f)
    
    dirty = False
    variants = prod.get("variants", [])
    parent_inr = prod.get("current_price") or prod.get("current_price_inr") or 0
    parent_usd = float(prod.get("source_price") or prod.get("source_price_usd") or 0.0)
    
    var_inr_prices = []
    var_usd_prices = []
    
    for v in variants:
        # Resolve INR price
        v_inr = v.get("price") or v.get("current_price") or v.get("price_inr") or parent_inr
        v_inr = int(round(float(v_inr)))
        if v.get("price") != v_inr:
            v["price"] = v_inr
            dirty = True
        if v.get("current_price") != v_inr:
            v["current_price"] = v_inr
            dirty = True
        if v.get("price_inr") != v_inr:
            v["price_inr"] = v_inr
            dirty = True
        var_inr_prices.append(v_inr)
        
        # Resolve USD price
        v_usd = v.get("source_price") or v.get("source_price_usd") or parent_usd
        v_usd = round(float(v_usd), 2)
        if v.get("source_price") != v_usd:
            v["source_price"] = v_usd
            dirty = True
        if v.get("source_price_usd") != v_usd:
            v["source_price_usd"] = v_usd
            dirty = True
        var_usd_prices.append(v_usd)

    # Set price range if multi-price
    if var_inr_prices:
        min_inr = min(var_inr_prices)
        max_inr = max(var_inr_prices)
        if min_inr < max_inr:
            new_inr_range = {"min": min_inr, "max": max_inr}
            if prod.get("price_range_inr") != new_inr_range:
                prod["price_range_inr"] = new_inr_range
                dirty = True
                range_count += 1
        elif prod.get("price_range_inr") is not None:
            # If all variants have the same price, range is not needed
            prod["price_range_inr"] = None
            dirty = True

    if var_usd_prices:
        min_usd = min(var_usd_prices)
        max_usd = max(var_usd_prices)
        if min_usd < max_usd:
            new_usd_range = {"min": min_usd, "max": max_usd}
            if prod.get("price_range_usd") != new_usd_range:
                prod["price_range_usd"] = new_usd_range
                dirty = True
        elif prod.get("price_range_usd") is not None:
            prod["price_range_usd"] = None
            dirty = True

    if dirty:
        with open(pf, "w", encoding="utf-8") as f:
            json.dump(prod, f, indent=2, ensure_ascii=False)
        updated_count += 1

print(f"Updated {updated_count} product JSONs. Found {range_count} products with variant price ranges.")
