with open("product-updater/horizon_clean_theme/sections/header.liquid", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "data-menu-style" in line or "header__drawer" in line or "max-width: 989px" in line:
            print(f"{idx+1}: {line.strip()[:100]}")
