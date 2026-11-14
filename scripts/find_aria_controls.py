import os

root = "product-updater/horizon_clean_theme"
for dirpath, _, filenames in os.walk(root):
    for fn in filenames:
        fp = os.path.join(dirpath, fn)
        try:
            with open(fp, encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    if 'aria-controls="header-panel-' in line:
                        print(f"{fp}:{idx+1} {line.strip()[:100]}")
        except Exception:
            pass
