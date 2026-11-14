import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query IntrospectProductSetInput {
  __type(name: "ProductSetInput") {
    inputFields {
      name
      type {
        name
        kind
        ofType {
          name
          kind
        }
      }
    }
  }
}
"""

res, _, err = execute_shopify_graphql(query)
fields = res.get("__type", {}).get("inputFields", [])
print(f"Total input fields on ProductSetInput: {len(fields)}")
for f in fields:
    print(f"  - {f['name']}: {f['type']}")
