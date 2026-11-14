import sys
PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

def main():
    query = """
    {
      products(first: 20, query: "tag:beauty") {
        nodes {
          title
          vendor
          variants(first: 2) {
            nodes {
              price
            }
          }
        }
      }
    }
    """
    data, _, _ = execute_shopify_graphql(query)
    for p in data.get("products", {}).get("nodes", []):
        v_prices = [f"₹{float(v['price']):,.0f}" for v in p["variants"]["nodes"]]
        print(f"{p['vendor']:<18} | {p['title'][:35]:<35} | {', '.join(v_prices)}")

if __name__ == "__main__":
    main()
