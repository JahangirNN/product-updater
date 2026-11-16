import requests
import json

GRAPHQL_URL = "https://www.jomashop.com/graphql"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Accept': '*/*',
}

WATCH_QUERY = """
query getWatchMedia($urlKey: String!) {
  products(filter: { url_key: { eq: $urlKey } }) {
    items {
      id
      sku
      name
      url_key
      stock_status
      image {
        label
        url_nocache
      }
      media_gallery {
        ... on ProductImage {
          url_nocache
          label
        }
      }
    }
  }
}
"""

watches = [
    "tissot-watch-t099-207-22-118-02",
    "seiko-prospex-chronograph-quartz-blue-dial-mens-watch-ssc965",
    "citizen-promaster-dive-quartz-black-dial-mens-watch-bn0264-53e"
]

for w in watches:
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": WATCH_QUERY, "variables": {"urlKey": w}},
        headers=headers,
        timeout=15
    )
    print(f"Watch {w}: HTTP {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("data", {}).get("products", {}).get("items", [])
        if items:
            item = items[0]
            print(f"  Name: {item.get('name')}")
            print(f"  Stock: {item.get('stock_status')}")
            print(f"  Image: {item.get('image')}")
            print(f"  Media gallery: {item.get('media_gallery')}")
        else:
            print("  No items returned!")
    else:
        print("  Error response:", resp.text[:200])
