import os

root = "product-updater/scratch"
for fn in os.listdir(root):
    if fn.endswith(".py"):
        fp = os.path.join(root, fn)
        with open(fp, encoding="utf-8") as f:
            c = f.read()
            if "publication" in c.lower() and "mutation" in c.lower():
                print(f"--- {fn} ---")
                for line in c.split("\n"):
                    if any(k in line.lower() for k in ["mutation", "execute", "publication"]):
                        print(" ", line.strip()[:100])
