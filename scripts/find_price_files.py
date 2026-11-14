import os

root = "product-updater/horizon_clean_theme"
for dirpath, _, filenames in os.walk(root):
    for fn in filenames:
        if "price" in fn.lower():
            print(os.path.join(dirpath, fn))
