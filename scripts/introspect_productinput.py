import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query IntrospectProductInput {
  __type(name: "ProductInput") {
    inputFields {
      name
      type {
        name
        kind
      }
    }
  }
}
"""

res, _, err = execute_shopify_graphql(query)
fields = res.get("__type", {}).get("inputFields", [])
print(f"Total input fields on ProductInput: {len(fields)}")
for f in fields:
    if any(k in f["name"].lower() for k in ["publish", "status", "store"]):
        print(f"  - {f['name']}: {f['type']}")
