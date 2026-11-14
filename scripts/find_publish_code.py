import os

root = "product-updater"
for dirpath, _, filenames in os.walk(root):
    for fn in filenames:
        if fn.endswith(".py"):
            fp = os.path.join(dirpath, fn)
            with open(fp, encoding="utf-8") as f:
                c = f.read()
                if "publish" in c.lower() and "graphql" in c.lower():
                    print(fp)
