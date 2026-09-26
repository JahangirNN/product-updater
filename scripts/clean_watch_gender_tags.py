import sys, os, json, re, time
sys.path.insert(0, '.')
from storage.shopify_auth import execute_shopify_graphql

mut_remove = '''
mutation tagsRemove($id: ID!, $tags: [String!]!) {
  tagsRemove(id: $id, tags: $tags) {
    node { id }
    userErrors { field message }
  }
}
'''

mut_add = '''
mutation tagsAdd($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) {
    node { id }
    userErrors { field message }
  }
}
'''

def fetch_all_products():
    cursor = None
    all_products = []
    while True:
        after_clause = f', after: \"{cursor}\"' if cursor else ''
        q = f"""{{
          products(first: 250{after_clause}) {{
            pageInfo {{
              hasNextPage
              endCursor
            }}
            edges {{
              node {{
                id
                title
                vendor
                productType
                tags
              }}
            }}
          }}
        }}"""
        data, ext, err = execute_shopify_graphql(q)
        edges = data['products']['edges']
        all_products.extend([e['node'] for e in edges])
        if not data['products']['pageInfo']['hasNextPage']:
            break
        cursor = data['products']['pageInfo']['endCursor']
    return all_products

def clean_gender_tags():
    products = fetch_all_products()
    print(f'Total products scanned: {len(products)}')
    fixed = 0
    for p in products:
        pid = p['id']
        title = p['title']
        vendor = p['vendor']
        tags = set(p['tags'])

        is_women_title = bool(re.search(r'\b(women|women\'s|womens|ladies|lady)\b', title, re.I))
        is_men_title = bool(re.search(r'\b(men|men\'s|mens)\b', title, re.I)) and not is_women_title

        if is_men_title:
            conflicting = tags.intersection({'Women', "Women's", 'Gender:Women', "Gender:Women's", 'Ladies', 'Unisex', 'Gender:Unisex'})
            if conflicting:
                print(f'[FIX MEN] {vendor} - {title}: removing {list(conflicting)}')
                execute_shopify_graphql(mut_remove, variables={'id': pid, 'tags': list(conflicting)})
                execute_shopify_graphql(mut_add, variables={'id': pid, 'tags': ['Men', "Men's", 'Gender:Men', "Gender:Men's"]})
                fixed += 1
                time.sleep(0.1)

        elif is_women_title:
            conflicting = tags.intersection({'Men', "Men's", 'Gender:Men', "Gender:Men's", 'Unisex', 'Gender:Unisex'})
            if conflicting:
                print(f'[FIX WOMEN] {vendor} - {title}: removing {list(conflicting)}')
                execute_shopify_graphql(mut_remove, variables={'id': pid, 'tags': list(conflicting)})
                execute_shopify_graphql(mut_add, variables={'id': pid, 'tags': ['Women', "Women's", 'Gender:Women', "Gender:Women's", 'Ladies']})
                fixed += 1
                time.sleep(0.1)

    print(f'Done. Cleaned {fixed} products.')

if __name__ == '__main__':
    clean_gender_tags()
