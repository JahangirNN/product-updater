import os
import glob
import json
import statistics

PROJECT_ROOT = "product-updater"

for store in ["jdsports", "footlocker", "katespade"]:
    store_dir = os.path.join(PROJECT_ROOT, "storage", "db", store, "products")
    files = glob.glob(os.path.join(store_dir, "*.json"))
    prices = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        p = float(d.get("source_price") or d.get("price_current") or 0.0)
        if p > 0:
            prices.append(p)
    if prices:
        print(f"Store: {store.upper()} ({len(prices)} items with price)")
        print(f"  Min USD: ${min(prices):.2f} | Max USD: ${max(prices):.2f} | Median: ${statistics.median(prices):.2f} | Mean: ${statistics.mean(prices):.2f}")
        # Distribution
        under_50 = sum(1 for p in prices if p < 50)
        p_50_100 = sum(1 for p in prices if 50 <= p < 100)
        p_100_150 = sum(1 for p in prices if 100 <= p < 150)
        p_150_plus = sum(1 for p in prices if p >= 150)
        print(f"  Bands: <$50: {under_50} | $50-100: {p_50_100} | $100-150: {p_100_150} | >$150: {p_150_plus}")
