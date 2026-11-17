import sys
sys.path.insert(0, 'product-updater')
from storage.shopify_auth import execute_shopify_graphql

COLLECTION_CREATE_MUTATION = """
mutation collectionCreate($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection {
      id
      title
      handle
      productsCount {
        count
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

COLLECTIONS_TO_CREATE = [
    {
        "title": "Luxury Watches",
        "handle": "watches",
        "descriptionHtml": "<p>Explore authenticated luxury Swiss timepieces and chronographs.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TYPE", "relation": "CONTAINS", "condition": "Watch"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Watch"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Watches"}
            ]
        }
    },
    {
        "title": "Designer Handbags & Bags",
        "handle": "bags",
        "descriptionHtml": "<p>Discover iconic designer handbags, shoulder bags, and luxury totes.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TYPE", "relation": "CONTAINS", "condition": "Bag"},
                {"column": "TYPE", "relation": "CONTAINS", "condition": "Tote"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Handbag"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Bags"}
            ]
        }
    },
    {
        "title": "Luxury Perfumes & Fragrances",
        "handle": "fragrances",
        "descriptionHtml": "<p>Curated luxury perfumes, eau de parfums, and fragrance gift sets.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TYPE", "relation": "CONTAINS", "condition": "Perfume"},
                {"column": "TYPE", "relation": "CONTAINS", "condition": "Fragrance"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Fragrance"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Perfume"}
            ]
        }
    }
]

for col in COLLECTIONS_TO_CREATE:
    print(f"Creating /collections/{col['handle']}...")
    res, ext, err = execute_shopify_graphql(COLLECTION_CREATE_MUTATION, variables={"input": col})
    if err:
        print(f"  Error: {err}")
    else:
        u_errors = res.get("collectionCreate", {}).get("userErrors", [])
        if u_errors:
            print(f"  UserErrors: {u_errors}")
        else:
            c = res["collectionCreate"]["collection"]
            print(f"  ✓ Success! Created {c['title']} ({c['id']}) handle: /collections/{c['handle']}")
