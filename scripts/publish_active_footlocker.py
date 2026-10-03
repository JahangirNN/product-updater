import sys, os, glob, json, time
sys.path.insert(0, r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql

ONLINE_STORE_PUB_ID = "gid://shopify/Publication/328164671654"

pub_mutation = """
mutation bulkPub($query: String!) {
  productBulkPublish(
    search: $query,
    publicationIds: ["gid://shopify/Publication/328164671654"]
  ) {
    userErrors {
      field
      message
    }
  }
}
"""

def publish_all_footlocker():
    id_list = []
    files = glob.glob("storage/db/footlocker/products/*.json")
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        # Publish all active products (availability in_stock)
        if d.get("shopify_product_id") and d.get("availability") == "in_stock":
            gid = d["shopify_product_id"]
            num_id = gid.split("/")[-1]
            id_list.append(num_id)
            
    # Deduplicate
    id_list = sorted(list(set(id_list)))
    print(f"Total active Foot Locker products to publish: {len(id_list)}")

    chunk_size = 50
    for i in range(0, len(id_list), chunk_size):
        chunk = id_list[i:i+chunk_size]
        query_str = " OR ".join(f"id:{pid}" for pid in chunk)
        print(f"Publishing chunk {i//chunk_size + 1}/{(len(id_list) + chunk_size - 1)//chunk_size} ({len(chunk)} items)...")
        res, _, err = execute_shopify_graphql(pub_mutation, {"query": query_str})
        if err or (res and res.get("productBulkPublish", {}).get("userErrors")):
            print("  Error:", err or res.get("productBulkPublish", {}).get("userErrors"))
        else:
            print("  --> Chunk queued successfully")
        time.sleep(1)

    print("All chunks submitted! Waiting 10s for Shopify asynchronous publish processing...")
    time.sleep(10)

    # Verification query
    print("Verifying publication status for sample products...")
    verify_query = """
    query checkPublished($query: String!) {
      products(first: 10, query: $query) {
        edges {
          node {
            id
            title
            vendor
            publishedOnPublication(publicationId: "gid://shopify/Publication/328164671654")
          }
        }
      }
    }
    """
    for vendor in ["adidas", "ASICS", "Nike"]:
        res, _, _ = execute_shopify_graphql(verify_query, {"query": f"vendor:'{vendor}'"})
        edges = res.get("products", {}).get("edges", []) if res else []
        print(f"Vendor {vendor} sample products:")
        for edge in edges:
            node = edge["node"]
            pub = node.get("publishedOnPublication")
            print(f"  [{node['vendor']}] {node['title'][:35]} | Online Store Published: {pub}")

if __name__ == "__main__":
    publish_all_footlocker()
