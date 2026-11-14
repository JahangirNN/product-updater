import sys

with open("product-updater/horizon_clean_theme/snippets/luxury-sidebar-panels.liquid", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if 'id="header-panel-' in line:
            print(f"{i+1}: {line.strip()}")
