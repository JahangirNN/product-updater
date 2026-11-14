import os

for fn in os.listdir("product-updater/scripts"):
    if fn.startswith("publish_"):
        fp = os.path.join("product-updater/scripts", fn)
        with open(fp, encoding="utf-8") as f:
            c = f.read()
            for line in c.split("\n"):
                if "mutation" in line.lower() or "publish" in line.lower():
                    if len(line.strip()) < 80:
                        print(f"{fn}: {line.strip()}")
