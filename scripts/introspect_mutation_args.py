import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query IntrospectMutationField {
  __schema {
    mutationType {
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
}
"""

data, ext, err = execute_shopify_graphql(query)
if data:
    for f in data['__schema']['mutationType']['fields']:
        if f['name'] in ['productBulkPublish', 'collectionBulkPublish', 'publishablePublish']:
            print(f['name'], ":", [(a['name'], a['type']) for a in f['args']])
