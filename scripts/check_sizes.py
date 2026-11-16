import os

def get_dir_size(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                total += os.path.getsize(fp)
    return total

for p in ["product-updater/storage/db", "dropship-scraper/venv", "extracted_theme", "theme_download.zip"]:
    if os.path.exists(p):
        if os.path.isfile(p):
            sz = os.path.getsize(p)
        else:
            sz = get_dir_size(p)
        print(f"{p:30s}: {sz / (1024*1024):.2f} MB")
