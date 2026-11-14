import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query IntrospectMutations {
  __type(name: "Mutation") {
    fields {
      name
      args {
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
}
"""

res, _, err = execute_shopify_graphql(query)
fields = res.get("__type", {}).get("fields", [])
print(f"Total mutation fields: {len(fields)}")
for f in fields:
    name = f["name"]
    if "publish" in name.lower():
        print(f"Mutation: {name}")
        for arg in f.get("args", []):
            print(f"  - {arg['name']}: {arg['type']}")
