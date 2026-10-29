import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

# Check shop metafields or apps
query = """
query {
  appInstallations(first: 20) {
    edges {
      node {
        app {
          title
          handle
        }
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query)
if data:
    for edge in data['appInstallations']['edges']:
        app = edge['node']['app']
        print(f"App: {app['title']} ({app['handle']})")
else:
    print("Err:", err)
