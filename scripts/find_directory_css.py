with open("product-updater/horizon_clean_theme/snippets/luxury-desktop-nav.liquid", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "luxury-directory" in line:
            print(f"{idx+1}: {line.strip()[:100]}")
