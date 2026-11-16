import json
import os
import datetime

index_path = r"C:\workspace\dropship-scraper-portable-20260905\product-updater\storage\db\index.json"
with open(index_path, "r", encoding="utf-8") as f:
    catalog = json.load(f)

total_products = len(catalog)
print(f"Total products in catalog index: {total_products}")

now = datetime.datetime.now(datetime.timezone.utc)

never_checked = []
stale_over_6h = []
stale_over_24h = []
recently_checked = []
stores_breakdown = {}

for p_id, p_info in catalog.items():
    store = p_info.get("store") or p_info.get("source_store", "unknown")
    stores_breakdown[store] = stores_breakdown.get(store, 0) + 1

    last_checked_str = p_info.get("last_checked") or p_info.get("verified_at") or p_info.get("updated_at")
    if not last_checked_str:
        never_checked.append((p_id, p_info))
        continue

    try:
        # Parse ISO timestamp
        ts = last_checked_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(ts)
        age_hours = (now - dt).total_seconds() / 3600.0

        if age_hours > 24:
            stale_over_24h.append((p_id, p_info, age_hours))
        elif age_hours > 6:
            stale_over_6h.append((p_id, p_info, age_hours))
        else:
            recently_checked.append((p_id, p_info, age_hours))
    except Exception as e:
        never_checked.append((p_id, p_info))

print("\nStore Breakdown:")
for s, count in sorted(stores_breakdown.items(), key=lambda x: x[1], reverse=True):
    print(f"  {s}: {count} products")

print(f"\nFreshness Status (relative to current UTC time {now.isoformat()}):")
print(f"  Checked within last 6 hours: {len(recently_checked)} ({len(recently_checked)/total_products*100:.1f}%)")
print(f"  Checked between 6 - 24 hours: {len(stale_over_6h)}")
print(f"  Stale over 24 hours:        {len(stale_over_24h)}")
print(f"  Never checked:              {len(never_checked)}")

if never_checked:
    print("\nSample never checked products:")
    for p_id, p_info in never_checked[:5]:
        print(f"  - {p_id}: {p_info.get('title')} ({p_info.get('store')})")

if stale_over_24h:
    print("\nSample stale over 24h products:")
    for p_id, p_info, age in stale_over_24h[:5]:
        print(f"  - {p_id}: {p_info.get('title')} ({p_info.get('store')}) - {age:.1f}h ago")

if recently_checked:
    ages = [a for _, _, a in recently_checked]
    print(f"\nRecently checked stats:")
    print(f"  Min age: {min(ages):.2f} hours ({min(ages)*60:.1f} mins)")
    print(f"  Max age: {max(ages):.2f} hours")
    print(f"  Avg age: {sum(ages)/len(ages):.2f} hours")
