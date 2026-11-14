import os

for fn in os.listdir("product-updater/scripts"):
    if fn.endswith(".py"):
        fp = os.path.join("product-updater/scripts", fn)
        with open(fp, encoding="utf-8") as f:
            c = f.read()
            if "shopify_navigation_manifest" in c:
                print(f"{fn} references shopify_navigation_manifest")
