import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query IntrospectMutations {
  __schema {
    mutationType {
      fields {
        name
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
if data and data.get('__schema'):
    fields = [f['name'] for f in data['__schema']['mutationType']['fields']]
    matching = [f for f in fields if any(k in f.lower() for k in ['publish', 'channel', 'catalog'])]
    print("Matching mutations:", matching)
else:
    print("Error:", err)
