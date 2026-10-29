import os
import sys
import glob
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import prepare_product_set_payload

target = None
for f in glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products", "*.json")):
    with open(f, "r", encoding="utf-8") as fp:
        d = json.load(fp)
    if "nell-fringe" in d.get("handle", ""):
        target = d
        break

payload = prepare_product_set_payload(target, 95.0)
print("Payload files count:", len(payload.get("files", [])))
for i, f in enumerate(payload.get("files", [])):
    print(f"  File {i}: {f}")

print("\nPayload variants count:", len(payload.get("variants", [])))
for i, v in enumerate(payload.get("variants", [])):
    print(f"  Variant {i}: options={v.get('optionValues')} file={v.get('file')}")
