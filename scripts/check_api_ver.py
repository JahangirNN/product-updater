with open("product-updater/storage/shopify_auth.py", encoding="utf-8") as f:
    text = f.read()

for line in text.split("\n"):
    if "api_version" in line.lower() or "endpoint" in line.lower() or "graphql" in line.lower():
        print(line[:100])
