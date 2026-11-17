import sys, os
sys.path.insert(0, r"c:\workspace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql

mut = """
mutation collectionUpdate($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection {
      id
      title
      handle
      productsCount {
        count
      }
      ruleSet {
        appliedDisjunctively
        rules {
          column
          relation
          condition
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

res, _, err = execute_shopify_graphql(mut, variables={
    "input": {
        "id": "gid://shopify/Collection/691311575206",
        "title": "Luxury Perfumes & Fragrance Sets",
        "descriptionHtml": "<p>Discover our curated collection of luxury perfumes, signature extrait de parfums, and fragrance gift sets.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Fragrance"},
                {"column": "TYPE", "relation": "EQUALS", "condition": "Perfume"},
                {"column": "TYPE", "relation": "EQUALS", "condition": "Body Mist & Hair Mist"},
                {"column": "TYPE", "relation": "EQUALS", "condition": "Travel Size & Mini Cologne"},
                {"column": "TAG", "relation": "EQUALS", "condition": "men-perfume-set"}
            ]
        }
    }
})

print("Result:", res)
print("Err:", err)
