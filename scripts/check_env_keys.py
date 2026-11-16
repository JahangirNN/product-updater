import os

for env_path in ["product-updater/.env", "dropship-scraper/.env"]:
    if os.path.exists(env_path):
        print(f"Keys in {env_path}:")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key = line.split("=", 1)[0].strip()
                    print(f"  {key}")
