import os
import sys

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

import storage.shopify_sync as ss

print("shopify_sync exports:")
for name in dir(ss):
    if not name.startswith("_"):
        print(f"  - {name}")
